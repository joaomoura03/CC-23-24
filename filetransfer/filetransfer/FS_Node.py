from argparse import ArgumentParser
from pathlib import Path

from filetransfer.node import Node
from filetransfer.utils import Address


def main():
    parser = ArgumentParser(description="File Transfer")

    parser.add_argument("storage_folder", type=str, help="File storage folder")
    parser.add_argument("server_host", type=str, help="Server host")
    parser.add_argument("server_port", type=int, help="Server port")
    args = parser.parse_args()

    storage_path = Path(__file__).parents[0] / "file_system" / args.storage_folder
    print(args)

    node = Node(
        storage_path=storage_path,
        server_address=Address(args.server_host, args.server_port),
    )

    # node.regist()

    choice = input("Escolha uma operação:\n1 - Atualizar Node\n2 - Informação Ficheiros\
			\n3 - Ask file\n4 - Fechar\n")

    if choice == '1':
        node.regist()
    
    elif choice == '2':
        node.get_file_info()
    
    elif choice == '4':
        node.close()

if __name__ == "__main__":
    main()
