from argparse import ArgumentParser

from node import Node
from utils import Address


def main():
    parser = ArgumentParser(description="File Transfer")

    parser.add_argument("storage_folder", type=str, help="File storage folder")
    parser.add_argument("server_host", type=str, help="Server host")
    parser.add_argument("server_port", type=int, help="Server port")

    args = parser.parse_args()
    print(
        f"Conexão FS Track Protocol com servidor {args.server_host} porta"
        f" {args.server_port}."
    )
    

    node = Node(
        storage_folder=args.storage_folder,
        server_address=Address(host=args.server_host, port=args.server_port),
    )

    try:
        while True:
            choice = input(
                "Escolha uma operação:\n1 - Atualizar Node\n2 - Informação Ficheiros   "
                "             \n3;(file_name) - Descarregar Ficheiro\n4 - Fechar\n"
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
    except KeyboardInterrupt:
        pass
    finally:
        node.close()


if __name__ == "__main__":
    main()
