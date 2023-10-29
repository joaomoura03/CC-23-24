import socket

HOST = '10.4.4.1'
PORT = 9090

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_socket.bind((HOST, PORT))

server_socket.listen()

print(f"Server is listening on {HOST}:{PORT}")

while True:
    client_socket, client_address = server_socket.accept()
    
    print(f"Accepted connection from {client_address}")

    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        
        print(f"Received: {data.decode('utf-8')}")

        response = "Received your message: " + data.decode('utf-8')
        client_socket.sendall(response.encode('utf-8'))
    
    client_socket.close()
    