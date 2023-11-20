import socket

import csv
import json


# HOST = '10.4.4.1'
HOST = 'localhost'
PORT = 9090

store_file_path = "FS_Data.csv"

# Open socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))

server_socket.listen()

print(f"Server is listening on {HOST}:{PORT}")

while True:
    # Accept client connection
    client_socket, client_address = server_socket.accept()

    data = client_socket.recv(1024)
    if not data:
        break

    received = data.decode('utf-8')

    if received[0] == '1':
        with open(store_file_path, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=';')
            csvwriter.writerow([client_address[0]] + received[2:].split(";"))
        print(f"Nodo {client_address[0]} registado")
        response = "Successfully registered: " + client_address[0]
        client_socket.sendall(response.encode('utf-8'))

    elif received[0] == '2':
        this_dict = {}
        with open(store_file_path, 'r', newline='') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            for row in csvreader:
                i = 2
                m = len(row)
                while i < m:
                    this_dict.setdefault(row[i], [])
                    this_dict[row[i]].append((row[0], row[i+1]))
                    i += 2
        keys = list(this_dict.keys())
        json_data = json.dumps(list(this_dict.keys()))
        response = json_data.encode()
        client_socket.sendall(response)

        data = client_socket.recv(1024)
        if not data:
            break
        received = data.decode('utf-8')
        index = int(received[2:])

        if 0 <= index <= len(keys):
            json_data = json.dumps(this_dict[keys[index]])

            print("dict")
            print(this_dict)
            print("this_dict[index]") 
            print(this_dict[keys[index]])

            response = json_data.encode()
            client_socket.sendall(response)

    else:
        response = "Operação inválida"
        client_socket.sendall(response)
        break #BREAK PARA FACILITAR TESTES


    client_socket.close()
    print(f"Closed client socket with {client_address}")

server_socket.close()