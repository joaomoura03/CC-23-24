from datetime import datetime, timedelta
from typing import Any, Optional
import socket

from pydantic import BaseModel, Field, PrivateAttr, model_serializer, model_validator, field_serializer, field_validator

PACKET_ACK_TIMEOUT = 5

FileName = str
Url = str
PacketId = int
BlockId = int


class Address(BaseModel):
    host: str = socket.gethostbyname(socket.gethostname())
    port: int

    @model_serializer()
    def serialize(self):
        return f"{self.host}:{self.port}"

    @model_validator(mode="before")
    @classmethod
    def parse_address(cls, data: Any) -> Any:
        if isinstance(data, str) and ":" in data:
            host, port = data.split(":")
            return {"host": host, "port": port}
        return data

    def __hash__(self) -> int:
        return hash((self.host, self.port))

    def get(self) -> tuple[str, int]:
        if self.host == "127.0.1.1":
            return "127.0.0.1", self.port
        return self.host, self.port


class FileNode(BaseModel):
    host: str
    port: int
    blocks: list[int]


class File(BaseModel):
    name: str
    nodes: dict[Url, FileNode]

    def add_node(self, *, node: FileNode) -> "File":
        self.nodes[f"{node.host}:{node.port}"] = node
        return self


class FileCatalog(BaseModel):
    files: dict[FileName, File] = Field(default_factory=dict)

    def __getitem__(self, file_name: FileName) -> File:
        return self.files[file_name]

    def add_file(self, *, file: File) -> "FileCatalog":
        self.files[file.name] = file
        return self

    def add_file_node(self, *, file_node: FileNode, file_name: str) -> "FileCatalog":
        if file_name not in self.files:
            self.add_file(file=File(name=file_name, nodes={}))
        self.files[file_name].add_node(node=file_node)
        return self

    def list_files(self) -> list[FileName]:
        return list(self.files.keys())

    def get_file_nodes(self, *, file_name: FileName) -> list[FileNode]:
        return list(self.files[file_name].nodes.values())

    def save(self, *, path: str) -> None:
        with open(path, mode="w", encoding="utf-8") as fp:
            fp.write(self.model_dump_json())

    @classmethod
    def load(cls, *, path: str) -> "FileCatalog":
        with open(path, mode="r", encoding="utf-8") as fp:
            return cls.model_validate_json(fp.read())


class FilePeers(BaseModel):
    info: dict[int, Address] = Field(default_factory=dict)

    def __getitem__(self, block: int) -> Address:
        return self.info[block]

    @classmethod
    def from_file(cls, file: File) -> "FilePeers":
        file_peers = cls()
        for node in file.nodes.values():
            for block in node.blocks:
                if block not in file_peers.info:
                    file_peers.info[block] = Address(host=node.host, port=node.port)
        return file_peers


class PacketInfo(BaseModel):
    file_name: FileName
    block_id: BlockId
    packet_id: PacketId = 0

    def to_bytes(self) -> bytes:
        return (
            f"{self.file_name};{self.block_id};{self.packet_id}".encode("utf-8")
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "PacketInfo":
        print(data.decode("utf-8"))
        print(data.decode("utf-8").split(";"))
        file_name, block_id, packet_id = data.decode("utf-8").split(";")
        return cls(file_name=file_name, block_id=int(block_id), packet_id=int(packet_id))


class SentPacket(BaseModel):
    packet_id: PacketId
    data: bytes
    _sent_at: datetime = PrivateAttr(default_factory=datetime.now)

    def to_bytes(self) -> bytes:
        return f"{self.packet_id};".encode("utf-8") + self.data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "SentPacket":
        packet_id, data = data.split(b";", 1)
        return cls(packet_id=int(packet_id), data=data)

    def __eq__(self, other: "SentPacket") -> bool:
        return self.packet_id == other.packet_id and self.data == other.data

    def should_resend(self) -> bool:
        return self._sent_at + timedelta(seconds=PACKET_ACK_TIMEOUT) < datetime.now()

    def update(self) -> None:
        self._sent_at = datetime.now()


class SentBlock(BaseModel):
    block_id: BlockId
    packets: dict[PacketId, SentPacket]

    def add_packet(self, *, packet: SentPacket) -> "SentBlock":
        self.packets[packet.packet_id] = packet
        return self

    def remove_packet(self, *, packet_id: PacketId) -> "SentBlock":
        if packet_id in self.packets:
            self.packets.pop(packet_id)
        return self


class SentFile(BaseModel):
    file_name: FileName
    blocks: dict[BlockId, SentBlock]

    def add_block(self, *, block: SentBlock) -> "SentFile":
        self.blocks[block.block_id] = block
        return self
    
    def remove_packet(self, *, block_id: BlockId, packet_id: PacketId) -> "SentBlock":
        if block_id in self.blocks:
            self.blocks[block_id].remove_packet(packet_id=packet_id)
        if not self.blocks[block_id].packets:
            self.blocks.pop(block_id)
        return self


class SentClient(BaseModel):
    client_address: Address
    files: dict[FileName, SentFile]

    def add_file(self, *, file: SentFile) -> "SentClient":
        self.files[file.file_name] = file
        return self
    
    def remove_packet(self, *, packet_info: PacketInfo) -> "SentBlock":
        if packet_info.file_name in self.files:
            self.files[packet_info.file_name].remove_packet(block_id=packet_info.block_id, packet_id=packet_info.packet_id)
        if not self.files[packet_info.file_name].blocks:
            self.files.pop(packet_info.file_name)
        return self


class SentCatalog(BaseModel):
    clients: dict[Address, SentClient] = Field(default_factory=dict)

    def add_file(self, *, client: Address, file: SentFile) -> "SentCatalog":
        if client not in self.clients:
            self.clients[client] = SentClient(client_address=client, files={})
        self.clients[client].add_file(file=file)
        return self

    def add_block(
        self, *, client: Address, file_name: FileName, block: SentBlock
    ) -> "SentCatalog":
        if client not in self.clients or file_name not in self.clients[client].files:
            self.add_file(client=client, file=SentFile(file_name=file_name, blocks={}))
        self.clients[client].files[file_name].add_block(block=block)
        return self

    def remove_packet(self, *, packet_info: PacketInfo, client: Address) -> "SentCatalog":
        if client in self.clients:
            self.clients[client].remove_packet(packet_info=packet_info)
        if not self.clients[client].files:
            self.clients.pop(client)
        return self

    def get_next_packet(self, *, packet_info: PacketInfo, client: Address) -> Optional[SentPacket]:
        try:
            return (
                self.clients[client]
                .files[packet_info.file_name]
                .blocks[packet_info.block_id]
                .packets[packet_info.packet_id + 1]
            )
        except KeyError:
            return None


def int_to_bytes(number: int, length: int = 4) -> bytes:
    return number.to_bytes(length, byteorder="little")


def bytes_to_int(number: bytes) -> int:
    return int.from_bytes(number, byteorder="little")


def is_socket_alive(s: socket.socket) -> bool:
    try:
        data = s.recv(1, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        if not data:
            return False
    except BlockingIOError:
        return True
    except ConnectionResetError:
        return False
    except Exception as e:
        return True
    return True