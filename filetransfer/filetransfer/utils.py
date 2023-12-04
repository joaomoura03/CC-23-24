from dataclasses import dataclass

from pydantic import BaseModel

FileName = str
Host = str


@dataclass
class Address:
    host: str
    port: int

class TransferFile(BaseModel):
    name: str = ""
    info: dict[int, Address] = {}

    def __getitem__(self, block: int) -> Address:
        return self.info[block]

    def add(self, *, host: str, port: str, block: int):
        if block not in self.info:
            self.info[block] = Address(host=host, port=port)

class FileNode(BaseModel):
    host: str
    port: str
    blocks: list[int]


class File(BaseModel):
    name: str
    nodes: dict[Host, FileNode]

    def add_node(self, *, node: FileNode) -> None:
        self.nodes[node.host] = node


class FileCatalog(BaseModel):
    files: dict[FileName, File]

    def __getitem__(self, file_name: FileName) -> File:
        return self.files[file_name]

    def add_file(self, *, file: File) -> None:
        self.files[file.name] = file

    def add_file_node(self, *, file_node: FileNode, file_name: str):
        if file_name in self.files:
            self[file_name].add_node(node=file_node)
        else:
            self.files[file_name] = File(
                name=file_name, nodes={file_node.host: file_node}
            )

    def list_files(self) -> list[FileName]:
        return list(self.files.keys())
    
    def get_file_info(self, *, file_name: FileName) -> str:
        return list(self.files[file_name].nodes.values())
            
        