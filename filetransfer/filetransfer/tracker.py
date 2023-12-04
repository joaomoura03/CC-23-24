import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from filetransfer.utils import FileCatalog, FileName, FileNode

BUFFER_SIZE = 1024


def get_store_path():
    return Path(__file__).parents[1] / "assets" / "FS_Data.json"


class Tracker:
    server_socket: socket.socket
    store_path: Path
    store: FileCatalog
    store_lock: Lock
    save_lock: Lock
    thread_pool: ThreadPoolExecutor
    running: bool

    def __init__(
        self,
        *,
        host: str = socket.gethostbyname(socket.gethostname()),
        port: int = 9090,
        store_path: Path = get_store_path(),
        n_threads: int = 10,
    ) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.store_path = store_path
        self.save_lock = Lock()
        self.store_lock = Lock()
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)
        self.running = False
        self.load()

    def close(self):
        self.server_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)

    def start(self):
        self.running = True
        while self.running:
            print(f"Servidor ativo em {self.server_socket.getsockname()}")
            self.server_socket.listen()
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection from {client_address}")
            data = client_socket.recv(BUFFER_SIZE)
            print(data)
            self.thread_pool.submit(self.handle_client, data.decode("utf-8"), client_socket, client_address)

    def stop(self):
        self.running = False

    def save(self):
        with open(self.store_path, mode="w", encoding="utf-8") as fp:
            fp.write(self.store.model_dump_json())

    def load(self):
        with open(self.store_path, mode="r", encoding="utf-8") as fp:
            self.store = FileCatalog.model_validate_json(fp.read())

    def handle_client(self, data: str, client_socket: socket.socket, client_address: str):
        logging.debug(f"Received {data}")
        if data:
            response = self.callback(
                client_address=client_address[0],
                data=data,
            )
            print(f"Sending {response}")
            client_socket.sendall(response.encode("utf-8"))
        client_socket.close()

    def callback(self, *, client_address: str, data: str) -> str:
        if data[0] == "1":
            return self.regist_node(
                client_address=client_address, node_raw_info=data
            )
        if data[0] == "2":
            return self.list_files()
        if data[0] == "3":
            return self.file_info(file_name=data[2:])
        return "ERROR"

    def regist_node(self, *, client_address: str, node_raw_info: str) -> str:
        split_data = node_raw_info.split(";")
        port = split_data[1]
        splits = len(split_data)
        if splits > 2:
            for i in range(2, splits, 2):
                file_name = split_data[i]
                blocks = [int(b) for b in split_data[i + 1].split(",")]
                file_node = FileNode(host=client_address, port=port, blocks=blocks)
                with self.save_lock:
                    self.store.add_file_node(file_node=file_node, file_name=file_name)
            with self.store_lock:
                self.save()
            print(f"Nodo {client_address} registado")
            return f"OK {client_address}"
        return "No files"

    def list_files(self) -> str:
        print("Lista de ficheiros")
        with self.save_lock:
            return str(self.store.list_files())

    def file_info(self, *, file_name: FileName) -> str:
        print(f"Informação de {file_name}")
        with self.save_lock:
            return ";".join(str((file_node.host, file_node.port, str(file_node.blocks))) for file_node in self.store.get_file_info(file_name=file_name))
