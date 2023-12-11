from filetransfer.utils import Address, SentBlock, SentFile, SentPacket
from filetransfer.node import UDP_BUFFER_SIZE, PACKET_SIZE


def test_save_load():
    c1 = Address(host="12.0.3.1", port=9091)
    c2 = Address(host="12.0.3.1", port=9091)
    f1 = "file1.txt"
    f2 = "file2.txt"

    f1_b1_p1 = SentPacket(packet_id=1, data=b"f1_b1_p1")
    f1_b1_p2 = SentPacket(packet_id=2, data=b"f1_b1_p2")
    f1_b2_p1 = SentPacket(packet_id=1, data=b"f1_b2_p1")
    f1_b2_p2 = SentPacket(packet_id=2, data=b"f1_b2_p2")
    f2_b1_p1 = SentPacket(packet_id=1, data=b"f2_b1_p1")

    c1_f1_b1 = SentBlock(block_id=1, packets=[f1_b1_p1, f1_b1_p2])
    c1_f1_b2 = SentBlock(block_id=2, packets=[f1_b2_p1, f1_b2_p2])
    c1_f2_b1 = SentBlock(block_id=1, packets=[f2_b1_p1])
    c2_f2_b1 = SentBlock(block_id=1, packets=[f2_b1_p1])

    c1_f1 = SentFile(client=c1, file_name=f1, blocks=[c1_f1_b1, c1_f1_b2])
    c1_f2 = SentFile(client=c1, file_name=f2, blocks=[c1_f2_b1])
    c2_f2 = SentFile(client=c2, file_name=f2, blocks=[c2_f2_b1])

def test_packet_size():
    data = bytes(UDP_BUFFER_SIZE)
    packet = SentPacket(packet_id=1, data=data)
    packet_str = packet.model_dump_json()
    assert len(packet_str) <= UDP_BUFFER_SIZE
