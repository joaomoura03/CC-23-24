import json
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

PACKET_ACK_TIMEOUT = 5

FileName = str
Url = str
PacketId = int
BlockId = int


@dataclass
class Address:
    port: int
    host: str = socket.gethostbyname(socket.gethostname())

    def to_string(self) -> str:
        return f'"{self.host}:{self.port}"'

    @classmethod
    def from_string(cls, address_string: str) -> "Address":
        address = address_string[1:-1]
        return cls(host=address.split(":")[0], port=int(address.split(":")[1]))

    def __hash__(self) -> int:
        return hash((self.host, self.port))

    def get(self) -> tuple[str, int]:
        if self.host == "127.0.1.1":
            return "127.0.0.1", self.port
        return self.host, self.port


@dataclass
class FileNode:
    host: str
    port: int
    blocks: list[int]

    def to_json(self) -> str:
        return (
            "{"
            + f'"host":"{self.host}","port":{self.port},"blocks":{json.dumps(self.blocks)}'
            + "}"
        )

    @classmethod
    def from_json(cls, node_string: str, mode: str) -> "FileNode":
        parts = node_string[1:-1].split(",", 2)
        if mode == "address":
            host = dns_host_to_address(parts[0].split(":")[1][1:-1])
        elif mode == "host":
            host = parts[0].split(":")[1][1:-1]
        return cls(
            host=host,
            port=int(parts[1].split(":")[1]),
            blocks=json.loads(parts[2].split(":")[1]),
        )


@dataclass
class File:
    name: str
    nodes: dict[Url, FileNode]

    def add_node(self, *, node: FileNode) -> "File":
        self.nodes[f"{node.host}:{node.port}"] = node
        return self

    def to_json(self) -> str:
        return (
            "{"
            + f'"name":"{self.name}","nodes":'
            + "{"
            + ",".join([
                f"\"{url}\":{node.to_json()}" for url, node in self.nodes.items()
            ])
            + "}}"
        )

    @classmethod
    def from_json(cls, file_string: str, mode: str) -> "File":
        parts = file_string.split(",", 1)
        nodes = parts[1].split(":", 1)[1][:-2].split("}")

        return cls(
            name=parts[0].split(":")[1][1:-1],
            nodes={
                node[1:].split(":", 2)[0][1:]
                + ":"
                + node.split(":", 2)[1][:-1]: FileNode.from_json(
                    node.split(":", 2)[2] + "}", mode
                )
                for node in nodes
                if node
            },
        )


@dataclass
class FileCatalog:
    files: dict[FileName, File]

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

    def to_json(self) -> str:
        return (
            "{"
            + f'"files":'
            + "{"
            + ",".join([
                f'"{file_name}":{file.to_json()}'
                for file_name, file in self.files.items()
            ])
            + "}}"
        )

    @classmethod
    def from_json(cls, catalog_string: str) -> "FileCatalog":
        content = catalog_string[1:-2].split(":", 1)[1]
        split = content.split("}")[:-3]
        file_names = []
        files = []
        j = i = c = 0
        max = len(split)
        while i < max:
            file_names.append(split[i].split(":", 1)[0][2:-1])
            files.append(split[i].split(":", 1)[1])
            j = i + 1
            while j < max and split[j]:
                files[c] += "}" + split[j]
                j += 1
            files[c] += "}}}"
            i = j + 2
            c += 1
        return cls(
            files={
                file_names[i]: File.from_json(files[i], mode="host")
                for i in range(len(files))
            }
        )

    def save(self, *, path: str) -> None:
        with open(path, mode="w", encoding="utf-8") as fp:
            fp.write(self.to_json())

    @classmethod
    def load(cls, *, path: str) -> "FileCatalog":
        with open(path, mode="r", encoding="utf-8") as fp:
            return cls.from_json(fp.read())


@dataclass
class FilePeers:
    info: dict[int, Address]

    def __getitem__(self, block: int) -> Address:
        return self.info[block]

    @classmethod
    def from_file(cls, file: File) -> "FilePeers":
        file_peers = cls(info={})
        for node in file.nodes.values():
            for block in node.blocks:
                if block not in file_peers.info:
                    file_peers.info[block] = Address(
                        host=dns_host_to_address(node.host), port=node.port
                    )
        return file_peers


@dataclass
class PacketInfo:
    file_name: FileName
    block_id: BlockId
    packet_id: PacketId = 0

    def to_bytes(self) -> bytes:
        return f"{self.file_name};{self.block_id};{self.packet_id}".encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "PacketInfo":
        file_name, block_id, packet_id = data.decode("utf-8").split(";")
        return cls(
            file_name=file_name, block_id=int(block_id), packet_id=int(packet_id)
        )


class SentPacket:
    packet_id: PacketId
    data: bytes
    sent_at: datetime

    def __init__(self, *, packet_id: PacketId, data: bytes):
        self.packet_id = packet_id
        self.data = data
        self.sent_at = datetime.now()

    def to_bytes(self) -> bytes:
        return f"{self.packet_id};".encode("utf-8") + self.data

    @classmethod
    def from_bytes(cls, data: bytes) -> "SentPacket":
        packet_id, data = data.split(b";", 1)
        return cls(packet_id=int(packet_id), data=data)

    def __eq__(self, other: "SentPacket") -> bool:
        return self.packet_id == other.packet_id and self.data == other.data

    def should_resend(self) -> bool:
        return self.sent_at + timedelta(seconds=PACKET_ACK_TIMEOUT) < datetime.now()

    def update(self) -> None:
        self.sent_at = datetime.now()


@dataclass
class SentBlock:
    block_id: BlockId
    packets: dict[PacketId, SentPacket]

    def add_packet(self, *, packet: SentPacket) -> "SentBlock":
        self.packets[packet.packet_id] = packet
        return self

    def remove_packet(self, *, packet_id: PacketId) -> "SentBlock":
        if packet_id in self.packets:
            self.packets.pop(packet_id)
        return self


@dataclass
class SentFile:
    file_name: FileName
    blocks: dict[BlockId, SentBlock]

    def add_block(self, *, block: SentBlock) -> "SentFile":
        self.blocks[block.block_id] = block
        return self

    def remove_packet(self, *, block_id: BlockId, packet_id: PacketId) -> "SentFile":
        if block_id in self.blocks:
            self.blocks[block_id].remove_packet(packet_id=packet_id)
        if not self.blocks[block_id].packets:
            self.blocks.pop(block_id)
        return self


@dataclass
class SentClient:
    client_address: Address
    files: dict[FileName, SentFile]

    def add_file(self, *, file: SentFile) -> "SentClient":
        self.files[file.file_name] = file
        return self

    def remove_packet(self, *, packet_info: PacketInfo) -> "SentClient":
        if packet_info.file_name in self.files:
            self.files[packet_info.file_name].remove_packet(
                block_id=packet_info.block_id, packet_id=packet_info.packet_id
            )
        if not self.files[packet_info.file_name].blocks:
            self.files.pop(packet_info.file_name)
        return self


@dataclass
class SentCatalog:
    clients: dict[Address, SentClient]

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

    def remove_packet(
        self, *, packet_info: PacketInfo, client: Address
    ) -> "SentCatalog":
        if client in self.clients:
            self.clients[client].remove_packet(packet_info=packet_info)
        if not self.clients[client].files:
            self.clients.pop(client)
        return self

    def get_next_packet(
        self, *, packet_info: PacketInfo, client: Address
    ) -> Optional[SentPacket]:
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


def dns_host_to_address(host: str) -> str:
    return socket.gethostbyname(host)


def address_to_dns_host(address: str) -> str:
    return socket.gethostbyaddr(address)[0]
