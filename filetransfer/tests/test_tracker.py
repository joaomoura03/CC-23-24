from filetransfer.tracker import get_store_path


def test_store_path():
    assert get_store_path().exists()
    assert get_store_path().is_file()
