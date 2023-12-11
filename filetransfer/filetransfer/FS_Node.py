from argparse import ArgumentParser

from filetransfer.node import Node
from filetransfer.utils import Address


def main():
    parser = ArgumentParser(description="File Transfer")

    parser.add_argument("storage_folder", type=str, help="File storage folder")
    parser.add_argument("server_host", type=str, help="Server host")
    parser.add_argument("server_port", type=int, help="Server port")
    parser.add_argument("c_port", type=int, help="REMOVE") #REMOVE ME
    args = parser.parse_args()

    node = Node(
        storage_folder=args.storage_folder,
        server_address=Address(args.server_host, args.server_port),
        port=args.c_port, #REMOVE ME
    )

    node.regist()
    print(
        f"Conexão FS Track Protocol com servidor {args.server_host} porta"
        f" {args.server_port}."
    )

    while True:
        choice = input(
            "Escolha uma operação:\n1 - Atualizar Node\n2 - Informação Ficheiros       "
            "         \n3;(file_name) - Descarregar Ficheiro\n4 - Fechar\n"
        )
        if choice == "1":
            node.udp_stop()
            node.regist()

        elif choice == "2":
            node.get_file_list()

        elif choice[0] == "3":
            node.get_file(file_name=choice[2:])

        elif choice == "4":
            node.close()
            break


if __name__ == "__main__":
    main()
