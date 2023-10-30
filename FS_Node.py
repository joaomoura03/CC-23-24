import socket
import sys

import os

def main():

    # Remove first argument (script name)
	args = sys.argv[1:] # args = main_folder serverIP Port

    # Open specified folder
	os.chdir(args[0])

	# Not implemented TCP 9090 default port
	HOST = args[1]
	PORT = args[2]
	
    # Open socket
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client_socket.connect((HOST, int(PORT)))
	
	
	print('FS Transfer Protocol: à escuta na porta UDP 9090')

	# Interaction while
	while True:
		# Add 2 - Pedir lista de ficherios\n3 - Pedir localização de ficheiro\n
		i = input("Escolha uma operação:\n1 - Registar Node\n4 - Cancelar\n")
		if (i == '1'):
			# Create message
			message = "1;9090;file1.txt;file2.txt"
			break

		# elif(i == '2'):
		# 	print("Não implementado")

		# elif(i == '3'):
		# 	print("Não implementado")

		elif(i == '4'):
			break

		else:
			print("Operação inválida!")

    # Send message
	client_socket.sendall(message.encode('utf-8'))

    # Receive and print response
	data = client_socket.recv(1024)
	print(f"Server response: {data.decode('utf-8')}")

    # Close socket
	client_socket.close()

if __name__ == "__main__":
	main()
