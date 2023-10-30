import socket

import csv


HOST = '10.4.4.1'
PORT = 9090

store_file_path = "FS_Data.csv"

# open socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))

server_socket.listen()

print(f"Server is listening on {HOST}:{PORT}")

while True:
    client_socket, client_address = server_socket.accept()

    print(f"FS Transfer Protocol: à escuta na porta {PORT}")


    print(f"Client address = {client_address[0]}")

    data = client_socket.recv(1024)
    if not data:
        break
   
    received = data.decode('utf-8')
    print(f"Received: {received}")

    if (received[0] == '1'):
        # Regist a new Node, isn't possible to regist a Node twice (remove or add files)
        with open(store_file_path, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=';')
            csvwriter.writerow([client_address[0]] + received[2:].split(";"))
            
    else:
        response = "Invalid Operation"

    response = "Received your message: " + received
    client_socket.sendall(response.encode('utf-8'))
    
    client_socket.close()
    print(f"Closed client socket with {client_address}")

server_socket.close()