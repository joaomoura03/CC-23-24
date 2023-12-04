import logging
import os
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from filetransfer.utils import TransferFile

from filetransfer.utils import Address

BUFFER_SIZE = 4
BLOCK_SIZE = 16


class Node:
    def __init__(
        self,
        *,
        storage_path: Path,
        server_address: Address,
        port: int = 9090,
        n_threads: int = 10,
    ):
        self.address = Address(socket.gethostbyname(socket.gethostname()), port)
        self.server_address = server_address
        self.transfer_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        self.transfer_socket.bind((self.address.host, self.address.port))
        self.storage_path = storage_path
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)
        self.running = False

    def close(self):
        self.server_socket.close()
        self.transfer_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)

    def udp_start(self):
        self.running = True
        while self.running:
            print(f"FS Transfer Protocol: à escuta na porta UDP {self.address.port}")
            data = self.transfer_socket.recvfrom(BUFFER_SIZE)
            self.thread_pool.submit(self.handle_client, data.decode("utf-8"))
    
    def udp_stop(self):
        self.running = False

    def udp_handler(self, data: str):
        print(data)
        file_name, block, host, port = data.split(";")
        file_path = self.storage_path / f"{file_name}"
        with open(file_path, mode="r") as fp:
            fp.seek(int(block) * BLOCK_SIZE)
            response = fp.read(BLOCK_SIZE)
        self.transfer_socket.sendto(response, (host, int(port)))
    
    def download(self, *, file_name: str, host: str, port: int, block: int) -> None:
        client_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        message = f"{file_name};{block};{self.address.host};{self.address.port}"
        client_socket.sendto(message.encode("utf-8"), (host, port))
        file_path = self.storage_path / f"{file_name}"
        with open(file_path, mode="rb+") as fp:
            fp.seek(block * BLOCK_SIZE)
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                fp.write(data)
        client_socket.close()

    def regist_file(self, file_path: Path) -> str:
        message = f"{file_path.name};"
        file_info = os.stat(file_path)
        file_size_bytes = file_info.st_size
        n_full_blocks = file_size_bytes // BLOCK_SIZE
        size_last_block = file_size_bytes % BLOCK_SIZE
        n_blocks = n_full_blocks + 1 if size_last_block > 0 else n_full_blocks
        message += ",".join(map(str, range(n_blocks)))
        return message

    def regist(self):
        self.server_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        self.server_socket.connect((self.server_address.host, self.server_address.port))
        files = self.storage_path.glob("**/*")
        message = f"1;{self.address.port};" + ";".join([
            self.regist_file(file) for file in files
        ])
        self.server_socket.sendall(message.encode("utf-8"))
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            received = data.decode("utf-8")
            print(f"Received {received}")
    
    def get_file_list(self) -> str:
        self.server_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        self.server_socket.connect((self.server_address.host, self.server_address.port))
        message = "2"
        self.server_socket.sendall(message.encode("utf-8"))
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            received = data.decode("utf-8")
            print(f"Received {received}")


    def get_file_info(self, *, file_name: str) -> str:
        self.server_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        self.server_socket.connect((self.server_address.host, self.server_address.port))
        message = f"3;{file_name}"
        self.server_socket.sendall(message.encode("utf-8"))
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            print(data.decode("utf-8"))
            return data.decode("utf-8")
        else:
            print("Ficheiro não encontrado")


    def get_file(self, *, file_name: str) -> None:
        split_data = self.get_file_info(file_name=file_name).split("'")
        tranfer_info = TransferFile()
        for i in range(1, len(split_data), 6):
            blocks = split_data[i+4]
            blocks = [int(block) for block in blocks[1:-1].split(",")]
            for block in blocks:
                tranfer_info.add(host=split_data[i], port=split_data[i+2], block=block)
        print(tranfer_info)
        self.udp_stop()
        for host, port, block in tranfer_info:
            self.thread_pool.submit(
                self.download, file_name=file_name, host=host, port=port, block=block
            )
        self.udp_start()
    