import socket
import threading
import struct
import json
import os

# Server configuration - configurable via environment variables
HOST = os.getenv('SERVER_HOST', '0.0.0.0')  # Listen on all interfaces
SCREEN_PORT = int(os.getenv('SCREEN_PORT', '12345'))
INPUT_PORT = int(os.getenv('INPUT_PORT', '12346'))

screen_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
input_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

screen_server.bind((HOST, SCREEN_PORT))
input_server.bind((HOST, INPUT_PORT))

screen_server.listen(2)
input_server.listen(2)

controlled_screen = None
controller_screen = None
controlled_input = None
controller_input = None

client_lock = threading.Lock()


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
    global controlled_screen, controller_screen, controlled_input, controller_input

    client_type = recvmsg(client_socket)
    print(f"Connection from {address} as {client_type}")

    with client_lock:
        if client_type == 'controlled_screen':
            controlled_screen = client_socket
            print("Controlled screen connected")
        elif client_type == 'controller_screen':
            controller_screen = client_socket
            print("Controller screen connected")
        elif client_type == 'controlled_input':
            controlled_input = client_socket
            print("Controlled input connected")
        elif client_type == 'controller_input':
            controller_input = client_socket
            print("Controller input connected")

        check_and_notify_connection()

    try:
        while True:
            size_data = recvall(client_socket, 4)
            if not size_data:
                break

            size = struct.unpack(">L", size_data)[0]
            data = recvall(client_socket, size)

            if not data:
                break

            with client_lock:
                if client_type == 'controlled_screen' and controller_screen:
                    try:
                        controller_screen.sendall(size_data + data)
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                        print("Controller screen disconnected while sending data")
                        controller_screen = None
                        break
                elif client_type == 'controller_input' and controlled_input:
                    try:
                        controlled_input.sendall(size_data + data)
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                        print("Controlled input disconnected while sending data")
                        controlled_input = None
                        break
    except Exception as e:
        print(f"Error handling client {client_type}: {e}")
    finally:
        with client_lock:
            if client_type == 'controlled_screen' and controlled_screen == client_socket:
                controlled_screen = None
                print("Controlled screen disconnected")
            elif client_type == 'controller_screen' and controller_screen == client_socket:
                controller_screen = None
                print("Controller screen disconnected")
            elif client_type == 'controlled_input' and controlled_input == client_socket:
                controlled_input = None
                print("Controlled input disconnected")
            elif client_type == 'controller_input' and controller_input == client_socket:
                controller_input = None
                print("Controller input disconnected")

        try:
            client_socket.close()
        except:
            pass


def check_and_notify_connection():
    if controlled_screen and controller_screen and controlled_input and controller_input:
        print("All connections established! Remote control session is active.")
        notification = {
            'type': 'connection_status',
            'status': 'complete'
        }
        try:
            sendmsg(controlled_screen, notification)
            sendmsg(controller_screen, notification)
            sendmsg(controlled_input, notification)
            sendmsg(controller_input, notification)
        except Exception as e:
            print(f"Error notifying clients: {e}")


def accept_screen_connections():
    while True:
        try:
            client_socket, addr = screen_server.accept()
            thread = threading.Thread(target=handle_client_packets, args=(client_socket, addr))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Error accepting screen connection: {e}")
            if screen_server.fileno() == -1:  # Socket closed
                break


def accept_input_connections():
    while True:
        try:
            client_socket, addr = input_server.accept()
            thread = threading.Thread(target=handle_client_packets, args=(client_socket, addr))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Error accepting input connection: {e}")
            if input_server.fileno() == -1:  # Socket closed
                break


def main():
    try:
        print(f"Server listening on {HOST}:{SCREEN_PORT} for screen and {HOST}:{INPUT_PORT} for input")
        print("Use Ctrl+C to stop the server")

        screen_thread = threading.Thread(target=accept_screen_connections)
        input_thread = threading.Thread(target=accept_input_connections)

        screen_thread.daemon = True
        input_thread.daemon = True

        screen_thread.start()
        input_thread.start()

        while True:
            command = input("Type 'quit' to stop the server: ")
            if command.lower() == 'quit':
                break
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        with client_lock:
            for client in [controlled_screen, controller_screen, controlled_input, controller_input]:
                if client:
                    try:
                        client.close()
                    except:
                        pass

        try:
            screen_server.close()
            input_server.close()
        except:
            pass

        print("Server shut down successfully")


if __name__ == "__main__":
    main()
