import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from filetransfer.utils import FileCatalog, FileName, FileNode

BUFFER_SIZE = 1024

#TODO criar dicionario com client_address:client_socket para so fechar o socket qd o client ficar inativo
#qd fechar socket?:
#fechar qd enviar fechar e ele envia fechar no try finally

def get_store_path():
    return Path(__file__).parents[1] / "assets" / "FS_Data.json"


class Tracker:
    server_socket: socket.socket
    store_path: Path
    store: FileCatalog
    disk_guard: Lock
    memory_guard: Lock
    thread_pool: ThreadPoolExecutor
    running: bool

    def __init__(
        self,
        *,
        host: str = socket.gethostbyname(socket.gethostname()),
        port: int = 9091,
        store_path: Path = get_store_path(),
        n_threads: int = 10,
    ) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.store_path = store_path
        self.memory_guard = Lock()
        self.disk_guard = Lock()
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)
        self.running = False
        self.load()

    def start(self):
        self.running = True
        while self.running:
            print(f"Servidor ativo em {self.server_socket.getsockname()}")
            self.server_socket.listen()
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection from {client_address}")
            self.thread_pool.submit(
                self.handle_client, client_socket, client_address
            )

    def stop(self):
        self.running = False

    def close(self):
        self.stop()
        self.server_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)

    def save(self):
        with open(self.store_path, mode="w", encoding="utf-8") as fp:
            fp.write(self.store.model_dump_json())

    def load(self):
        with open(self.store_path, mode="r", encoding="utf-8") as fp:
            self.store = FileCatalog.model_validate_json(fp.read())

    def handle_client(
        self, client_socket: socket.socket, client_address: str
    ):
        while data := client_socket.recv(BUFFER_SIZE).decode("utf-8"):
            response = self.callback(
                client_address=client_address[0],
                data=data,
            )
            print(f"Sending {response}")
            client_socket.sendall(response.encode("utf-8"))
        print(f"Connection from {client_address} closed")
        client_socket.close()

    def callback(self, *, client_address: str, data: str) -> str:
        if data[0] == "1":
            return self.regist_node(client_address=client_address, node_raw_info=data)
        if data[0] == "2":
            return self.list_files()
        if data[0] == "3":
            return self.file_info(file_name=data[2:])
        if data[0] == "4":
            self.close_node(client_address=client_address)
        return "ERROR"

    def regist_node(self, *, client_address: str, node_raw_info: str) -> str:
        split_data = node_raw_info.split(";")
        port = split_data[1]
        n_splits = len(split_data)
        if n_splits > 2:
            print(n_splits)
            for i in range(2, n_splits, 2):
                file_name = split_data[i]
                if not split_data[i+1]:
                    continue
                blocks = [int(b) for b in split_data[i + 1].split(",")]
                file_node = FileNode(host=client_address, port=port, blocks=blocks)
                with self.memory_guard:
                    self.store.add_file_node(file_node=file_node, file_name=file_name)
            with self.disk_guard:
                self.save()
            print(f"Nodo {client_address} registado")
            return f"OK {client_address}"
        return "No files"

    def list_files(self) -> str:
        print("Lista de ficheiros")
        with self.memory_guard:
            return str(self.store.list_files())

    def file_info(self, *, file_name: FileName) -> str:
        print(f"Informação de {file_name}")
        with self.memory_guard:
            return self.store[file_name].model_dump_json()
