import socket
import sys
import json

import os

def main():
    # Remove first argument (script name)
	args = sys.argv[1:] # args = main_folder serverIP Port
    # Open own folder
	os.chdir(args[0])

	# Tracker information
	SEND_HOST = args[1]
	# Usage of try to implement port TCP 9090 as default port
	try:
		SEND_PORT = int(args[2])
	except:
		SEND_PORT = 9090

	LISTEN_HOST = 'localhost'
	# UDP port to listen other Nodes
	LISTEN_PORT = 9090
	

	# Client Interaction while
	while True:
		# Open TCP socket to interact with Tracker
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client_socket.connect((SEND_HOST, SEND_PORT))

		# adicionar 2 - Pedir lista de ficherios\n3 - Pedir localização de ficheiro\n
		i = input("Escolha uma operação:\n1 - Registar Node\n4 - Cancelar\n")
		if i == '1':
			# Create message
			message = "1;9090;file1.txt;1,2;file2.txt;1,2"

			# Send message
			client_socket.sendall(message.encode('utf-8'))

			# Receive and print response
			data = client_socket.recv(1024)
			print(f"Server response: {data.decode('utf-8')}")

			break

		elif i == '2':
			# Create message
			message = "2"

			# Send message
			client_socket.sendall(message.encode('utf-8'))

			# Receive and print response
			data = client_socket.recv(1024)

			decoded_json = data.decode()
			decoded_strings = json.loads(decoded_json)

			print(f"Server response: {decoded_strings}")

			message = "3;" + input("File position: ")
			client_socket.sendall(message.encode('utf-8'))

			data = client_socket.recv(1024)
			decoded_json = data.decode()

			print(f"Server response: {decoded_json}")
			break

		elif i == '4':
			break

		else:
			print("Operação inválida!")

	# Close socket
	client_socket.close()

if __name__ == "__main__":
	main()