import socket
import sys

import os

def main():

    # remove first argument (script name)
	args = sys.argv[1:] # args = main_folder serverIP Port

    # open specified folder
	os.chdir(args[0])

	HOST = args[1]
	PORT = args[2]
	
    #create and connect socket
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client_socket.connect((HOST, int(PORT)))

	#while True:
		# i = input("Escolha uma operação:\n\
		# 	1 - Registar Node\n\
		# 	2 - Pedir lista de ficherios\n\
		# 	3 - Pedir localização de ficheiro\n\
		# 	4 - Cancelar")
		# match i:
		# 	case "1":
		# 		print("Não implementado")

		# 	case "2":
		# 		print("Não implementado")

		# 	case "3":
		# 		print("Não implementado")

		# 	case "4":
		# 		break

		# 	case _:
		# 		print("Operação inválida!")

    # create and send message
	message = "1,file1.txt,file2.txt"
	client_socket.sendall(message.encode('utf-8'))

    # receive and print response
	data = client_socket.recv(1024)
	print(f"Server response: {data.decode('utf-8')}")

    # close socket
	client_socket.close()

if __name__ == "__main__":
	main()

