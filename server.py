import socket
import threading
import struct
import json

# Server configuration
HOST = '192.168.1.0'
SCREEN_PORT = 12345
INPUT_PORT = 12346

# Initialize server sockets
screen_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
input_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

screen_server.bind((HOST, SCREEN_PORT))
input_server.bind((HOST, INPUT_PORT))

screen_server.listen(2)
input_server.listen(2)

# Client storage
controlled_screen = None
controller_screen = None
controlled_input = None
controller_input = None

def sendmsg(socket, key_data):
    data = json.dumps(key_data).encode()
    size = len(data)
    socket.sendall(struct.pack(">L", size) + data)

def recvmsg(socket):
    size_data = recvall(socket, 4)
    if not size_data:
        return None
    size = struct.unpack(">L", size_data)[0]
    data = recvall(socket, size)
    key_data = json.loads(data.decode())
    return key_data

def recvall(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(min(size - len(data), 4096))
        if not packet:
            return None
        data += packet
    return data


def handle_client_packets(client_socket, address):
    global controlled_screen,controller_screen,controlled_input,controller_input

    client_type = recvmsg(client_socket)
    print(f"Screen connection from {address} as {client_type}")

    if client_type == 'controlled_screen':
        controlled_screen = client_socket
    elif client_type == 'controller_screen':
        controller_screen = client_socket
    elif client_type == 'controlled_input':
        controlled_input = client_socket
    elif client_type == 'controller_input':
        controller_input = client_socket

    while True:
        #try:
            size_data = recvall(client_socket,4)
            if not size_data:
                break

            size = struct.unpack(">L", size_data)[0]
            data = recvall(client_socket, size)

            if not data:
                break

            if client_type == 'controlled_screen' and controller_screen:
                controller_screen.sendall(size_data + data)

            if client_type == 'controller_input' and controlled_input:
                controlled_input.sendall(size_data + data)

        #except Exception as e:
        #    print(f"Screen error: {e}")
        #    break

    if client_type == 'controlled':
        controlled_screen = None
    elif client_type == 'controller':
        controller_screen = None
    client_socket.close()

def accept_screen_connections():
    while True:
        client_socket, addr = screen_server.accept()
        thread = threading.Thread(target=handle_client_packets, args=(client_socket, addr))
        thread.start()


def accept_input_connections():
    while True:
        client_socket, addr = input_server.accept()
        thread = threading.Thread(target=handle_client_packets, args=(client_socket, addr))
        thread.start()


try:
    print(f"Server listening on {HOST}:{SCREEN_PORT} for screen and {HOST}:{INPUT_PORT} for input")
    screen_thread = threading.Thread(target=accept_screen_connections)
    input_thread = threading.Thread(target=accept_input_connections)

    screen_thread.start()
    input_thread.start()

    screen_thread.join()
    input_thread.join()

except Exception as e:
    print(f"Server error: {e}")
finally:
    if controlled_screen:
        controlled_screen.close()
    if controller_screen:
        controller_screen.close()
    if controlled_input:
        controlled_input.close()
    if controller_input:
        controller_input.close()
    screen_server.close()
    input_server.close()