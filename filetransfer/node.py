import os
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from time import sleep
from typing import Optional
import traceback

from utils import (
    Address,
    File,
    FilePeers,
    PacketInfo,
    SentBlock,
    SentCatalog,
    SentClient,
    SentPacket,
    is_socket_alive,
)

BUFFER_SIZE = 1024
BLOCK_SIZE = 16
PACKET_SIZE = 4
UDP_BUFFER_SIZE = PACKET_SIZE * 6 + 30
RECONNECT_MAX_TRIES = 5


class Node:
    server_socket: Optional[socket.socket] = None

    def __init__(
        self,
        *,
        storage_folder: str,
        server_address: Address,
        address: Address = Address(port=9090),
        n_threads: int = 10,
    ):
        self.address = address
        self.server_address = server_address
        self.transfer_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        self.transfer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.transfer_socket.bind(self.address.get())
        self.storage_path = (
            Path(__file__).parents[1] / "assets" / "file_system" / storage_folder
        )
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)
        self.running = False
        self.sent_packets = SentCatalog({})
        self.packet_guard = Lock()
        self.regist()

    def connect(self):
        self.server_socket = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        self.server_socket.connect(self.server_address.get())

    def send_to_server(self, message: str, retry_count: int = 1) -> None:
        try:
            if self.server_socket is None or not is_socket_alive(self.server_socket):
                self.connect()
            self.server_socket.sendall(message.encode("utf-8"))
        except Exception as e:
            self.disconnect_server()
            if retry_count <= RECONNECT_MAX_TRIES:
                print(
                    f"Servidor {self.server_address.to_string()} não disponível."
                    f"A tentar novamente em {retry_count} segundos"
                )
                sleep(retry_count)
                self.send_to_server(message=message, retry_count=retry_count + 1)

    def udp_packet_retry_one_client(self, *, client: SentClient):
        for file in client.files.values():
            for block in file.blocks.values():
                if not block.packets:
                    continue
                packet = list(block.packets.values())[0]
                if packet.should_resend():
                    self.send_packet(
                        packet=packet,
                        client_address=client.client_address,
                    )
                    packet.update()

    def udp_packet_retry(self):
        print("FR A verificar pacotes...")
        try:
            while self.running:
                sleep(5)
                with self.packet_guard:
                    for client in self.sent_packets.clients.values():
                        self.udp_packet_retry_one_client(client=client)
        except Exception as e:
            traceback.print_exc()
            print(e)
            os._exit(1)

    def udp_start(self):
        try:
            self.thread_pool.submit(self.udp_packet_retry)
            self.running = True
            while self.running:
                print(f"FS Transfer Protocol: à escuta UDP em {self.address.get()}")
                data, address = self.transfer_socket.recvfrom(UDP_BUFFER_SIZE)
                self.thread_pool.submit(
                    self.udp_handler,
                    data=data,
                    client_address=Address(host=address[0], port=address[1]),
                )
        except Exception as e:
            import os
            import traceback

            traceback.print_exc()
            print(e)
            os._exit(1)

    def udp_stop(self):
        self.running = False

    def disconnect_server(self):
        self.server_socket.close()
        self.server_socket = None

    def disconnect_transfer(self):
        self.transfer_socket.close()
        self.transfer_socket = None

    def close(self):
        self.udp_stop()
        self.disconnect_server()
        self.disconnect_transfer()
        self.thread_pool.shutdown(wait=False, cancel_futures=True)
        os._exit(0)

    def udp_handler(self, *, data: bytes, client_address: Address):
        try:
            packet_info = PacketInfo.from_bytes(data[1:])
            if data[0] == b"1"[0]:
                self.file_request_handler(
                    packet_info=packet_info,
                    client_address=client_address,
                )
            elif data[0] == b"2"[0]:
                self.packet_ack_handler(
                    packet_info=packet_info,
                    client_address=client_address,
                )
            else:
                print("Error", data)
        except Exception as e:
            import os
            import traceback

            traceback.print_exc()
            print(e)
            os._exit(1)

    def file_request_handler(self, *, packet_info: PacketInfo, client_address: Address):
        print("A enviar ficheiro...")
        file_path = self.storage_path / f"{packet_info.file_name}"
        with open(file_path, mode="rb") as fp:
            fp.seek(packet_info.block_id * BLOCK_SIZE)
            packet_count = 0
            block = SentBlock(block_id=packet_info.block_id, packets={})
            while (packet := fp.read(PACKET_SIZE)) and packet_count < (
                BLOCK_SIZE // PACKET_SIZE
            ):
                block.add_packet(packet=SentPacket(packet_id=packet_count, data=packet))
                packet_count += 1
            with self.packet_guard:
                self.sent_packets.add_block(
                    client=client_address,
                    file_name=packet_info.file_name,
                    block=block,
                )
        self.send_packet(
            packet=self.sent_packets.get_next_packet(
                packet_info=packet_info, client=client_address
            ),
            client_address=client_address,
        )

    def packet_ack_handler(self, *, packet_info: PacketInfo, client_address: Address):
        with self.packet_guard:
            self.sent_packets.remove_packet(
                packet_info=packet_info, client=client_address
            )
        next_packet = self.sent_packets.get_next_packet(
            packet_info=packet_info, client=client_address
        )
        if next_packet:
            self.send_packet(packet=next_packet, client_address=client_address)
        else:
            self.transfer_socket.sendto(b"", client_address.get())

    def send_packet(self, *, packet: SentPacket, client_address: Address) -> None:
        def fail_packet() -> bool:
            import random

            if random.random() < 0.1:
                return True
            return False

        if not fail_packet():
            self.transfer_socket.sendto(packet.to_bytes(), client_address.get())
            print("Pacote enviado")
        else:
            print("Pacote falhou")

    def download(self, *, file_name: str, address: Address, block: int) -> None:
        try:
            client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            packet_info = PacketInfo(file_name=file_name, block_id=block, packet_id=-1)
            message = b"1" + packet_info.to_bytes()

            client_socket.sendto(message, address.get())
            file_path = self.storage_path / f"{block}_{file_name}"
            with open(file_path, mode="wb") as fp:
                while True:
                    print("A receber ficheiro...")
                    data, address = client_socket.recvfrom(UDP_BUFFER_SIZE)
                    if not data:
                        break
                    packet = SentPacket.from_bytes(data=data)
                    packet_info = PacketInfo(
                        file_name=file_name,
                        block_id=block,
                        packet_id=packet.packet_id,
                    )
                    ack = b"2" + packet_info.to_bytes()
                    client_socket.sendto(ack, address)
                    fp.write(packet.data)
        except Exception as e:
            import os
            import traceback

            traceback.print_exc()
            print(e)
            os._exit(1)

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
        self.send_to_server(message=message)
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            received = data.decode("utf-8")
            print(f"Resposta {received}")
        else:
            print("Erro ao registar")
        self.thread_pool.submit(self.udp_start)

    def get_file_list(self) -> None:
        message = "2"
        self.send_to_server(message=message)
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            received = data.decode("utf-8")
            print(f"Resposta {received}")

    def get_file_info(self, *, file_name: str) -> File:
        message = f"3;{file_name}"
        self.send_to_server(message=message)
        data = self.server_socket.recv(BUFFER_SIZE)
        if data:
            return File.from_json(data.decode("utf-8"), mode="address")
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

        futures = [
            self.thread_pool.submit(
                self.download,
                file_name=file_name,
                address=file_peers[block],
                block=block,
            )
            for block in file_peers.info
        ]
        for future in futures:
            future.result()
        self.merge_blocks(file_name=file_name, block_ids=file_peers.info.keys())
