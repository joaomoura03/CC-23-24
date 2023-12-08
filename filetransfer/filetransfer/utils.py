from dataclasses import dataclass

from pydantic import BaseModel, Field

FileName = str
Url = str


@dataclass
class Address:
    host: str
    port: int


class FileNode(BaseModel):
    host: str
    port: str
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