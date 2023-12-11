from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel, PrivateAttr, Field

from typing import Optional

FileName = str
Url = str
PacketId = int
BlockId = int


@dataclass(frozen=True)
class Address:
    host: str
    port: int

    def get(self) -> tuple[str, int]:
        if self.host == "127.0.0.1":
            return "127.0.1.1", self.port
        return self.host, self.port


class FileNode(BaseModel):
    host: str
    port: int
    blocks: list[int]


class File(BaseModel):
    name: str
    nodes: dict[Url, FileNode]

    def add_node(self, *, node: FileNode) -> None:
        self.nodes[f"{node.host}:{node.port}"] = node


class FileCatalog(BaseModel):
    files: dict[FileName, File]

    def __getitem__(self, file_name: FileName) -> File:
        return self.files[file_name]

    def add_file(self, *, file: File) -> None:
        self.files[file.name] = file

    def add_file_node(self, *, file_node: FileNode, file_name: str):
        if file_name not in self.files:
            self.files[file_name] = File(name=file_name, nodes={})
        self[file_name].add_node(node=file_node)

    def list_files(self) -> list[FileName]:
        return list(self.files.keys())

    def get_file_info(self, *, file_name: FileName) -> str:
        return list(self.files[file_name].nodes.values())


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
    client: Address
    file_name: FileName
    block_id: BlockId
    packet_id: PacketId = 0


class SentPacket(BaseModel):
    packet_id: PacketId
    data: bytes
    _sent_at: datetime = PrivateAttr(default_factory=datetime.now)

    def should_resend(self) -> bool:
        return self._sent_at + timedelta(seconds=5) < datetime.now()

    def update(self) -> None:
        self._sent_at = datetime.now()


class SentBlock(BaseModel):
    block_id: BlockId
    packets: dict[PacketId, SentPacket]

    def add_packet(self, *, packet: SentPacket) -> None:
        self.packets[packet.packet_id] = packet


class SentFile(BaseModel):
    file_name: FileName
    blocks: dict[BlockId, SentBlock]

    def add_block(self, *, block: SentBlock) -> None:
        self.blocks[block.block_id] = block


class SentClient(BaseModel):
    client_address: Address
    files: dict[FileName, SentFile]

    def add_file(self, *, file: SentFile) -> None:
        self.files[file.file_name] = file


class SentCatalog(BaseModel):
    clients: dict[Address, SentClient] = Field(default_factory=dict)

    def add_file(self, *, client: Address, file: SentFile) -> None:
        if client not in self.clients:
            self.clients[client] = SentClient(client_address=client, files={})
        self.clients[client].add_file(file=file)
    
    def add_block(self, *, client: Address, file_name: FileName, block: SentBlock) -> None:
        if client not in self.clients or file_name not in self.clients[client].files:
            self.add_file(client=client, file=SentFile(file_name=file_name, blocks={}))
        self.clients[client].files[file_name].add_block(block=block)

    def remove_packet(self, *, packet_info: PacketInfo) -> None:
        try:
            self.clients[packet_info.client].files[packet_info.file_name].blocks[
                packet_info.block_id
            ].packets.pop(packet_info.packet_id)
        except KeyError:
            pass
    
    def get_next_packet(self, *, packet_info: PacketInfo) -> Optional[SentPacket]:
        try:
            return self.clients[packet_info.client].files[packet_info.file_name].blocks[
                    packet_info.block_id
                ].packets[packet_info.packet_id+1]
        except KeyError:
            return None


def int_to_bytes(number: int, length: int = 4) -> bytes:
    return number.to_bytes(length, byteorder="little")


def bytes_to_int(number: bytes) -> int:
    return int.from_bytes(number, byteorder="little")
