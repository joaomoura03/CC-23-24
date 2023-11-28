import socket
import logging

from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pydantic import BaseModel

from filetransfer.file import FileNode, File, FileCatalog

# HOST = '10.4.4.1'


def get_store_path():
    return Path(__file__).parents[1] / "assets" / "FS_Data.json"


class Tracker:
    server_socket: socket.socket
    store_path: Path
    store: FileCatalog
    store_lock: Lock
    save_lock: Lock
    thread_pool: ThreadPoolExecutor

    def __init__(
        self, *, host="localhost", port=9090, store_path="FS_Data.csv", n_threads=10
    ) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.store_path = Path(store_path)
        self.store_lock = Lock()
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)

    def close(self):
        self.server_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)

    def listen(self, *, callback):
        while True:
            self.server_socket.listen()
            client_socket, client_address = self.server_socket.accept()
            logging.info(f"Connection from {client_address}")
            data = client_socket.recv(1024)
            logging.debug(f"Received {data}")
            if data:
                response = self.thread_pool.submit(
                    callback,
                    client_address=client_address[0],
                    data=data.decode("utf-8"),
                )
                client_socket.sendall(response.encode("utf-8"))
            client_socket.close()

    def add_file_node(self, *, file_node: FileNode, file_name: str):
        with self.save_lock:
            if file_name in self.store.files:
                if file_node.host in self.store.files[file_name].nodes:
                    self.store.files[file_name].nodes[file_node.host].blocks = file_node.blocks
                else:
                    self.store.files[file_name].nodes.append(file_node)
            else:
                self.store.files[file_name] = File(name=file_name, nodes=[file_node])


    def regist_node(self, *, client_address: str, data: str):
        split_data = data.split(";")
        port = split_data[1]
        for i in range(2, len(split_data), 2):
            file_name = split_data[i]
            blocks = [int(b) for b in split_data[i + 1].split(",")]
            file_node = FileNode(host=client_address, port=port, blocks=blocks)
            Tracker.add_file_node(file_node=file_node, file_name=file_name)

        with self.store_lock:
            with open(self.store_file_path, "w") as fp:

                fp.write(self.store.model_dump_json())

        logging.info(f"Nodo {client_address} registado")
        return f"OK {client_address}"
