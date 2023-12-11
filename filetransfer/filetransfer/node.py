import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from time import sleep

from filetransfer.utils import Address, File, FilePeers, SentCatalog, int_to_bytes, PacketInfo, SentPacket, SentBlock

BUFFER_SIZE = 1024
BLOCK_SIZE = 16
PACKET_SIZE = 4
UDP_BUFFER_SIZE = PACKET_SIZE * 6 + 30


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
        self.storage_path = (
            Path(__file__).parents[1] / "assets" / "file_system" / storage_folder
        )
        self.thread_pool = ThreadPoolExecutor(max_workers=n_threads)
        self.running = False
        self.sent_packets = SentCatalog()
        self.packet_guard = Lock()

    


    def udp_packet_check(self):
        try:
            print("FR STARTING PACKET RECAP")
            while self.running:
                sleep(5)
                with self.packet_guard:
                    print("FR SENT PACKETS", self.sent_packets)
                    for client in self.sent_packets.clients.values():
                        for file in client.files.values():
                            for block in file.blocks.values():
                                l = list(block.packets.keys())
                                if len(l) > 0:
                                    packet = block.packets[l[0]]
                                    print("FR CHECKING PACKET", packet)
                                    if packet.should_resend():
                                        print(f"FR RESENDING PACKET {packet} to {client.client_address}")
                                        self.send_packet(
                                            packet=packet,
                                            client_address=client.client_address,
                                        )
                                        packet.update()
        except Exception as e:
            print(e)


    def udp_start(self):
        self.thread_pool.submit(self.packet_recap)
        self.running = True
        while self.running:
            print(f"FS Transfer Protocol: à escuta UDP em {self.address}")
            data, address = self.transfer_socket.recvfrom(UDP_BUFFER_SIZE)
            print("FR Recv [UDP_SERVER] TRANSFER", {address}, "-",data)
            print("FR HOST, PORT", address[0], address[1])
            print("FR address", Address(host=address[0], port=address[1]).get())
            self.thread_pool.submit(
                self.udp_handler,
                data=data.decode("utf-8"),
                client_address=Address(host=address[0], port=address[1])
            )


    def udp_stop(self):
        self.running = False


    def close(self):
        self.udp_stop()
        self.server_socket.close()
        self.transfer_socket.close()
        self.thread_pool.shutdown(wait=True, cancel_futures=False)


    def udp_handler(self, *, data: str, client_address: Address):
        try:
            print("FR Recv [UDP_SERVER] Transfer:",data)
            if data.startswith("1"):
                self.file_request_handler(packet_info=PacketInfo.model_validate_json(data[1:]), client_address=client_address)
            elif data.startswith("2"):
                self.packet_ack_handler(packet_info=PacketInfo.model_validate_json(data[1:]), client_address=client_address)
            else:
                print("Error")
        except Exception as e:
            print(e)
    

    def file_request_handler(self, *, packet_info: PacketInfo, client_address: Address):
        packet_info.client = client_address
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
                    client=packet_info.client,
                    file_name=packet_info.file_name,
                    block=block,
                )
        self.send_packet(
            packet=self.sent_packets.get_next_packet(packet_info=packet_info),
            client_address=client_address
        )


    def packet_ack_handler(self, *, packet_info: PacketInfo, client_address: Address):
        packet_info.client = client_address
        with self.packet_guard:
            self.sent_packets.remove_packet(packet_info=packet_info)
        next_packet = self.sent_packets.get_next_packet(packet_info=packet_info)
        if next_packet:
            self.send_packet(packet=next_packet, client_address=client_address)
        else:
            self.transfer_socket.sendto(b"", client_address.get())


    def send_packet(self, *, packet: SentPacket, client_address: Address) -> None:
        def fail_packet() -> bool:
            import random

            if random.random() < 0.5:
                return True
            return False
        if not fail_packet():
            print("FR SEND PACKET", packet)
            print("A enviar pacote...", packet.model_dump_json())
            print("FR Send [UDP_SERVER] TRANSFER", {client_address.get()}, "-",packet.model_dump_json())
            self.transfer_socket.sendto(packet.model_dump_json().encode("utf-8"), client_address.get())
            print("Pacote enviado")
        else:
            print("FR PACKET FAILED", packet)




    def download(self, *, file_name: str, address: Address, block: int) -> None:
        try:
            client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            packet_info = PacketInfo(
                client=self.address, file_name=file_name, block_id=block, packet_id=-1
            )
            message = f"1{packet_info.model_dump_json()}"
            print(f"Send to {address.get()} the message {message}")
            print("FR Send [UDP_CLIENT] CLIENT", {address.get()}, "-",message)
            
            client_socket.sendto(
                message.encode("utf-8"), address.get()
            )
            file_path = self.storage_path / f"{block}_{file_name}"
            with open(file_path, mode="wb") as fp:
                while True:
                    print("A receber ficheiro...")
                    data, address = client_socket.recvfrom(UDP_BUFFER_SIZE)
                    print("FR Recv [UDP_CLIENT] CLIENT", {address}, "-",data)
                    if not data:
                        break
                    packet = SentPacket.model_validate_json(data.decode("utf-8"))
                    packet_info = PacketInfo(client=self.address, file_name=file_name, block_id=block, packet_id=packet.packet_id)
                    ack = f"2{packet_info.model_dump_json()}"
                    print("FR Send [UDP_CLIENT] CLIENT", {address}, "-",ack)
                    client_socket.sendto(ack.encode("utf-8"), address)
                    fp.write(packet.data)
        except Exception as e:
            print(e)




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
