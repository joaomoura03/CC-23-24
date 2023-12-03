import logging
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from filetransfer.utils import Address

BUFFER_SIZE = 1024
BLOCK_SIZE = 16


class Node:
    def __init__(
        self,
        *,
        storage_path: Path,
        server_address: Address,
        port: int = 9091,
        n_threads: int = 10,
    ):
        self.address = Address(socket.gethostbyname(socket.gethostname()), port)
        self.server_address = server_address
        self.server_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        self.server_socket.connect((server_address.host, server_address.port))
        self.transfer_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        self.transfer_socket.bind((self.address.host, self.address.port))
        self.storage_path = storage_path
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)

    def close(self):
        self.server_socket.close()
        self.transfer_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)

    def regist_file(self, file_path: Path) -> str:
        message = f"{file_path.stem};"
        file_info = os.stat(file_path)
        file_size_bytes = file_info.st_size
        n_full_blocks = file_size_bytes // BLOCK_SIZE
        size_last_block = file_size_bytes % BLOCK_SIZE
        n_blocks = n_full_blocks + 1 if size_last_block > 0 else n_full_blocks
        message += ",".join(map(str, range(n_blocks)))
        return message

    def regist(self):
        files = self.storage_path.glob("**/*")
        message = f"1;{self.address.port};" + ";".join([
            self.regist_file(file) for file in files
        ])
        self.server_socket.sendall(message.encode("utf-8"))
        data = self.server_socket.recv(BUFFER_SIZE)
        print(f"Server response: {data.decode('utf-8')}")
        if data:
            received = data.decode("utf-8")
            logging.info(f"Received {received}")
    
    def get_file_info(self) -> str:
        message = "2"
        print(f"envia{message}")
        self.server_socket.sendall(message.encode("utf-8"))
        print("enviou")
        data = self.server_socket.recv(BUFFER_SIZE)
        print(data.decode("utf-8"))
        if data:
            logging.info(data.decode("utf-8"))
