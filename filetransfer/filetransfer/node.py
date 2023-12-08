import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from filetransfer.utils import Address, FilePeers, File

BUFFER_SIZE = 1024
BLOCK_SIZE = 16

UDP_BUFFER_SIZE = 4


class Node:
    def __init__(
        self,
        *,
        storage_folder: str,
        server_address: Address,
        port: int = 9093,
        n_threads: int = 10,
    ):
        self.address = Address(socket.gethostbyname(socket.gethostname()), port)
        self.server_address = server_address
        self.transfer_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        self.server_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        self.server_socket.connect((self.server_address.host, self.server_address.port))
        self.transfer_socket.bind((self.address.host, self.address.port))
        self.storage_path = Path(__file__).parents[1] / "assets" / "file_system" / storage_folder
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)
        self.running = False

    def udp_start(self):
        self.running = True
        while self.running:
            print(f"FS Transfer Protocol: à escuta UDP em {self.address}")
            data = self.transfer_socket.recvfrom(BUFFER_SIZE)
            print(data)
            self.thread_pool.submit(self.udp_handler, data)

    def udp_stop(self):
        self.running = False

    def close(self):

        self.udp_stop()
        self.server_socket.close()
        self.transfer_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)

    def udp_handler(self, data: str):
        def fail_packet() -> bool:
            import random
            if random.random() < 0.5:
                return True
            return False

        file_name, block = data[0].decode("utf-8").split(";")
        file_path = self.storage_path / f"{file_name}"
        with open(file_path, mode="rb") as fp:
            fp.seek(int(block) * BLOCK_SIZE)
            packet_count = 0
            while (packet := fp.read(UDP_BUFFER_SIZE)) and packet_count < (BLOCK_SIZE // UDP_BUFFER_SIZE):
                packet_count += 1
                if True:#not fail_packet():
                    self.transfer_socket.sendto(packet, data[1])
        self.transfer_socket.sendto(b"", data[1])

    def download(self, *, file_name: str, host: str, port: int, block: int) -> None:
        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        message = f"{file_name};{block}"
        print(f"Sendto {host, port} the message {message}")
        client_socket.sendto(message.encode("utf-8"), (host, port)) #to run on localhost change host to 127.0.1.1
        file_path = self.storage_path / f"{block}_{file_name}"
        with open(file_path, mode="wb") as fp:
            while True:
                print("A receber ficheiro...")
                data, address = client_socket.recvfrom(UDP_BUFFER_SIZE)
                if not data:
                    break
                fp.write(data)

    def regist_file(self, file_path: Path) -> str:
        message = f"{file_path.name};"
        file_size_bytes = file_path.stat().st_size
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
        if data:
            received = data.decode("utf-8")
            print(f"Received {received}")
        else:
            print("Erro ao registar")
        self.thread_pool.submit(self.udp_start)

    def get_file_list(self) -> None:
        message = "2"
        self.server_socket.sendall(message.encode("utf-8"))
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            received = data.decode("utf-8")
            print(f"Received {received}")

    def get_file_info(self, *, file_name: str) -> File:
        message = f"3;{file_name}"
        self.server_socket.sendall(message.encode("utf-8"))
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            print(data.decode("utf-8"))
            return File.model_validate_json(data.decode("utf-8"))
        print("Ficheiro não encontrado")

    def merge_blocks(self, *, file_name: str, block_ids: list[int]) -> None:
        file_path = self.storage_path / f"{file_name}"
        with open(file_path, mode="wb") as fp:
            for block_id in block_ids:
                path = self.storage_path / f"{block_id}_{file_name}"
                with open(path, mode="rb") as fp2:
                    fp.write(fp2.read())
                path.unlink()

    def get_file(self, *, file_name: str) -> None:
        print("A descarregar ficheiro...")
        file = self.get_file_info(file_name=file_name)
        if file is None:
            return
        file_peers = FilePeers.from_file(file=file)
        for block in file_peers.info:
            # self.thread_pool.submit(
            #     self.download,
            #     file_name=file_name,
            #     host=file_peers[block].host,
            #     port=int(file_peers[block].port),
            #     block=block
            # )
            #how to wait for this threads?
            self.download(
                file_name=file_name,
                host=file_peers[block].host,
                port=int(file_peers[block].port),
                block=block,
            )

        self.merge_blocks(file_name=file_name, block_ids=file_peers.info.keys())
