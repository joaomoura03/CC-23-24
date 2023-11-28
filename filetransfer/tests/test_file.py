from filetransfer.file import FileNode, File, FileCatalog
from pathlib import Path

def test_save_load(tmpdir):
    n1 = FileNode(host="12.0.3.1", port="9091", blocks=[1, 2, 3])
    n2 = FileNode(host="12.0.3.1", port="9091", blocks=[1, 3])
    n3 = FileNode(host="12.0.3.2", port="9093", blocks=[1, 2])
    n4 = FileNode(host="12.0.3.2", port="9093", blocks=[2, 3])
    n5 = FileNode(host="12.0.3.3", port="9094", blocks=[1, 2])
    n6 = FileNode(host="12.0.3.3", port="9094", blocks=[2, 3])
    n7 = FileNode(host="12.0.3.4", port="9095", blocks=[1, 3])
    f1_123 = File(name="file1.txt", nodes=[n1, n3])
    f1_13 = File(name="file2.txt", nodes=[n2, n4])
    f2_12 = File(name="file3.txt", nodes=[n5])
    f2_23 = File(name="file4.txt", nodes=[n6, n7])
    fc = FileCatalog(files={})
    fc.add(file=f1_123)
    fc.add(file=f1_13)
    fc.add(file=f2_12)
    fc.add(file=f2_23)

    file_path = Path(tmpdir) / "test_save_load.json"

    with open(file_path, "w") as fp:
        fp.write(fc.model_dump_json())

    with open(file_path, "r") as fp:
        fc2 = FileCatalog.model_validate_json(fp.read())
    
    assert fc == fc2