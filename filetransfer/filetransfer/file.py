from pydantic import BaseModel

FileName = str
Host = str

class FileNode(BaseModel):
    host: str
    port: str
    blocks: list[int]

class File(BaseModel):
    name: str
    nodes: dict[Host, FileNode]

class FileCatalog(BaseModel):
    files: dict[FileName, File]

    def add(self, *, file: File) -> None:
        self.files[file.name] = file


    def __getitem__(self, file_name: FileName) -> File:
        return self.files[file_name]