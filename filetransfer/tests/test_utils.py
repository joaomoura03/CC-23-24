from pathlib import Path

from filetransfer.utils import FileCatalog, FileNode


def test_save_load(tmpdir):
    n1 = FileNode(host="12.0.3.1", port="9091", blocks=[0, 1, 2])
    n2 = FileNode(host="12.0.3.1", port="9091", blocks=[0, 2])
    n3 = FileNode(host="12.0.3.2", port="9093", blocks=[0, 1])
    n4 = FileNode(host="12.0.3.2", port="9093", blocks=[1, 2])
    n5 = FileNode(host="12.0.3.3", port="9094", blocks=[0, 1])
    n6 = FileNode(host="12.0.3.3", port="9094", blocks=[1, 2])
    n7 = FileNode(host="12.0.3.4", port="9095", blocks=[0, 2])

    fc = FileCatalog(files={})

    fc.add_file_node(file_node=n1, file_name="file1.txt")
    fc.add_file_node(file_node=n3, file_name="file1.txt")
    fc.add_file_node(file_node=n2, file_name="file2.txt")
    fc.add_file_node(file_node=n4, file_name="file2.txt")
    fc.add_file_node(file_node=n5, file_name="file3.txt")
    fc.add_file_node(file_node=n6, file_name="file4.txt")
    fc.add_file_node(file_node=n7, file_name="file4.txt")

    file_path = Path(tmpdir) / "test_save_load.json"

    with open(file_path, "w") as fp:
        fp.write(fc.model_dump_json())

    with open(file_path, "r") as fp:
        fc2 = FileCatalog.model_validate_json(fp.read())

    assert fc == fc2
