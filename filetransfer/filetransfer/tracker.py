import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from filetransfer.utils import File, FileCatalog, FileName, FileNode

# HOST = '10.4.4.1'

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
        host: str = "localhost",
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
        running = True
        while running:
            self.server_socket.listen()
            client_socket, client_address = self.server_socket.accept()
            logging.info("Connection from %s", client_address)
            self.thread_pool.submit(self.handle_client, client_socket, client_address)

    def handle_client(self, client_socket: socket.socket, client_address: str):
        data = client_socket.recv(BUFFER_SIZE)
        print(f"Received {data}")
        logging.debug("Received %s", data)
        if data:
            response = self.callback(
                client_address=client_address[0],
                data=data.decode("utf-8"),
            )
            print(type(response))
            client_socket.sendall(response.encode("utf-8"))
        client_socket.close()

    def stop(self):
        self.running = False

    def save(self):
        with open(self.store_path, mode="w", encoding="utf-8") as fp:
            fp.write(self.store.model_dump_json())

    def load(self):
        with open(self.store_path, mode="r", encoding="utf-8") as fp:
            self.store = FileCatalog.model_validate_json(fp.read())

    def callback(self, *, client_address: str, data: str) -> str:
        if data[0] == "1":
            return self.regist_node(
                client_address=client_address, node_raw_info=data
            )
        if data[0] == "2":
            print("data[0]==2")
            return self.list_files()
        if data[0] == "3":
            return self.file_info(client_address=client_address, file_name=data)
        return "ERROR"

    def regist_node(self, *, client_address: str, node_raw_info: str) -> str:
        split_data = node_raw_info.split(";")
        port = split_data[1]
        for i in range(2, len(split_data), 2):
            file_name = split_data[i]
            blocks = [int(b) for b in split_data[i + 1].split(",")]
            file_node = FileNode(host=client_address, port=port, blocks=blocks)
            with self.save_lock:
                self.store.add_file_node(file_node=file_node, file_name=file_name)
        with self.store_lock:
            self.save()
        print("chegou")
        logging.info(f"Nodo {client_address} registado")
        return f"OK {client_address}"

    def list_files(self) -> list[FileName]:
        print("listar ficheiros")
        with self.store_lock:
            print(f"lista:{self.store.list_files()}")
            return self.store.list_files()

    def file_info(self, *, client_address: str, file_name: FileName) -> File:
        logging.info("Listando informação de %s para %s", file_name, client_address)
        with self.store_lock:
            return self.store[file_name]
