import time
from datetime import datetime
from pathlib import Path

from filetransfer.utils import (
    Address,
    File,
    FileCatalog,
    FileNode,
    FilePeers,
    SentBlock,
    SentCatalog,
    SentClient,
    SentFile,
    SentPacket,
    PACKET_ACK_TIMEOUT
)


def test_address_hash_equals():
    a1 = Address(host="1.2.3.4", port=9090)
    a2 = Address(host="1.2.3.4", port=9090)
    assert id(a1) != id(a2)
    assert hash(a1) == hash(a2)
    assert a1 == a2


def test_address_serialization():
    address = Address(host="1.2.3.4", port=1234)
    assert address.model_dump_json() == '"1.2.3.4:1234"'


def test_address_get():
    a1 = Address(host="1.2.3.4", port=9090)
    a2 = Address(host="127.0.0.1", port=9090)
    assert a1.get() == ("1.2.3.4", 9090)
    assert a2.get() == ("127.0.0.1", 9090)


def test_file_node():
    fn1 = FileNode(host="127.0.0.1", port="9090", blocks=[0, 1, 2])
    fn2 = FileNode(host="127.0.0.1", port="9090", blocks=[0, 1, 2])
    assert id(fn1) != id(fn2)
    assert fn1 == fn2


def test_file():
    fn1 = FileNode(host="127.0.0.1", port="9090", blocks=[0, 1, 2])
    fn2 = FileNode(host="127.0.0.1", port="9090", blocks=[0, 1, 2])
    assert id(fn1) != id(fn2)

    f1 = File(name="file1.txt", nodes={}).add_node(node=fn1)
    f2 = File(name="file1.txt", nodes={}).add_node(node=fn2)

    assert id(f1) != id(f2)
    assert f1 == f2


def test_file_catalog():
    fn1 = FileNode(host="4.3.2.1", port="4321", blocks=[0])
    fn2 = FileNode(host="1.2.3.4", port="1234", blocks=[1, 2])
    fn3 = FileNode(host="1.1.1.1", port="1111", blocks=[0, 1, 2])

    f1 = File(name="file1.txt", nodes={}).add_node(node=fn1).add_node(node=fn2)
    f2 = File(name="file2.txt", nodes={}).add_node(node=fn1).add_node(node=fn2)

    fc = FileCatalog().add_file(file=f1).add_file(file=f2)

    assert fc["file1.txt"] == f1
    assert fc["file2.txt"] == f2
    assert fc.get_file_nodes(file_name="file1.txt") == [fn1, fn2]
    assert fc.list_files() == ["file1.txt", "file2.txt"]

    fc.add_file_node(file_node=fn3, file_name="file3.txt")
    assert fc.list_files() == ["file1.txt", "file2.txt", "file3.txt"]


def test_file_catalog_save_load(tmpdir):
    n1 = FileNode(host="12.0.3.1", port="9091", blocks=[0, 1, 2])
    n2 = FileNode(host="12.0.3.1", port="9091", blocks=[0, 2])
    n3 = FileNode(host="12.0.3.2", port="9093", blocks=[0, 1])
    n4 = FileNode(host="12.0.3.2", port="9093", blocks=[1, 2])
    n5 = FileNode(host="12.0.3.3", port="9094", blocks=[0, 1])
    n6 = FileNode(host="12.0.3.3", port="9094", blocks=[1, 2])
    n7 = FileNode(host="12.0.3.4", port="9095", blocks=[0, 2])

    fc1 = FileCatalog()
    fc1.add_file_node(file_node=n1, file_name="file1.txt")
    fc1.add_file_node(file_node=n3, file_name="file1.txt")
    fc1.add_file_node(file_node=n2, file_name="file2.txt")
    fc1.add_file_node(file_node=n4, file_name="file2.txt")
    fc1.add_file_node(file_node=n5, file_name="file3.txt")
    fc1.add_file_node(file_node=n6, file_name="file4.txt")
    fc1.add_file_node(file_node=n7, file_name="file4.txt")

    file_path = Path(tmpdir) / "test_file_catalog_save_load.json"
    fc1.save(path=file_path)

    fc2 = FileCatalog.load(path=file_path)
    assert fc1 == fc2


def test_file_peers():
    fn1 = FileNode(host="1.2.3.4", port="1234", blocks=[0, 1])
    fn2 = FileNode(host="4.3.2.1", port="4321", blocks=[1, 2])
    f = File(name="file1.txt", nodes={}).add_node(node=fn1).add_node(node=fn2)
    fp1 = FilePeers.from_file(file=f)
    fp2 = FilePeers(
        info={
            0: Address(host="1.2.3.4", port=1234),
            1: Address(host="1.2.3.4", port=1234),
            2: Address(host="4.3.2.1", port=4321),
        }
    )
    assert fp1 == fp2


def test_sent_packet():
    dt1 = datetime.now()
    packet = SentPacket(packet_id=0, data=b"test")
    dt2 = datetime.now()

    assert packet.packet_id == 0
    assert packet.data == b"test"
    assert dt1 <= packet._sent_at <= dt2

    assert not packet.should_resend()
    time.sleep(PACKET_ACK_TIMEOUT)
    assert packet.should_resend()

    dt3 = datetime.now()
    packet.update()
    dt4 = datetime.now()

    assert dt2 <= packet._sent_at
    assert dt3 <= packet._sent_at <= dt4


def test_sent_catalog_save_load():
    a1 = Address(host="1.2.3.4", port=1234)
    a2 = Address(host="4.3.2.1", port=4321)
    f1 = "file1.txt"
    f2 = "file2.txt"

    f1_b0_p0 = SentPacket(packet_id=1, data=b"f1_b0_p0")
    f1_b0_p1 = SentPacket(packet_id=2, data=b"f1_b0_p1")
    f1_b1_p0 = SentPacket(packet_id=1, data=b"f1_b1_p0")
    f1_b1_p1 = SentPacket(packet_id=2, data=b"f1_b1_p1")
    f2_b0_p0 = SentPacket(packet_id=1, data=b"f2_b0_p0")

    c1_f1_b0 = SentBlock(block_id=0, packets={0: f1_b0_p0, 1: f1_b0_p1})
    c1_f1_b1 = SentBlock(block_id=1, packets={0: f1_b1_p0, 1: f1_b1_p1})
    c1_f2_b0 = SentBlock(block_id=0, packets={0: f2_b0_p0})
    c2_f2_b0 = SentBlock(block_id=0, packets={0: f2_b0_p0})

    c1_f1 = SentFile(file_name=f1, blocks={0: c1_f1_b0, 1: c1_f1_b1})
    c1_f2 = SentFile(file_name=f2, blocks={0: c1_f2_b0})
    c2_f2 = SentFile(file_name=f2, blocks={0: c2_f2_b0})

    c1 = SentClient(client_address=a1, files={f1: c1_f1, f2: c1_f2})
    c2 = SentClient(client_address=a2, files={f2: c2_f2})

    cl1 = SentCatalog(clients={a1: c1, a2: c2})
    json_catalog = cl1.model_dump_json()
    cl2 = SentCatalog.model_validate_json(json_catalog)
    assert cl1 == cl2

    json = c1.model_dump_json()
    l1 = SentClient.model_validate_json(json)
    assert c1 == l1

    json = c2.model_dump_json()
    l2 = SentClient.model_validate_json(json)
    assert c2 == l2


def test_packet_content():
    d1, d2 = bytes(10), bytes(20)
    p1 = SentPacket(packet_id=1, data=d1)
    p2 = SentPacket(packet_id=2, data=d2)
    p1_bytes = p1.to_bytes()
    p2_bytes = p2.to_bytes()
    assert len(p1_bytes) == 12
    assert len(p2_bytes) == 22
