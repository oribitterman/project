import socket
import pygame
import io
import struct
from PIL import Image
import threading
from pynput.keyboard import Listener
import json

# Server address
SERVER_HOST = '192.168.1.0'
SCREEN_PORT = 12345
INPUT_PORT = 12346

# Create two sockets
screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect both sockets
screen_socket.connect((SERVER_HOST, SCREEN_PORT))
input_socket.connect((SERVER_HOST, INPUT_PORT))

def sendmsg(socket, key_data):
    data = json.dumps(key_data).encode()
    print("data"+str(data))
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

# Send client type identifier
sendmsg(screen_socket, 'controller_screen')
sendmsg(input_socket, 'controller_input')


def recvall(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(min(size - len(data), 4096))
        if not packet:
            return None
        data += packet
    return data


def on_press(key):
    try:
        key_data = {
            'type': 'press',
            'key': str(key)
        }
        sendmsg(input_socket,key_data)
    except Exception as e:
        print(f"Error sending keypress: {e}")


def on_release(key):
    try:
        key_data = {
            'type': 'release',
            'key': str(key)
        }
        sendmsg(input_socket, key_data)
    except Exception as e:
        print(f"Error sending key release: {e}")


def handle_mouse():
    global screen
    # Add global variables to track previous button states
    global prev_left_state, prev_right_state

    if screen is None:
        return

    screen_width, screen_height = screen.get_size()
    x, y = pygame.mouse.get_pos()

    # Send mouse position
    mouse_data = {
        'type': 'move',
        'x': x / screen_width,
        'y': y / screen_height
    }
    sendmsg(input_socket, mouse_data)

    # Get current button states
    left, middle, right = pygame.mouse.get_pressed()

    # Only send left click events when state changes
    if left != prev_left_state:
        mouse_data = {
            'type': 'click',
            'button': 'left',
            'action': 'press' if left else 'release'
        }
        sendmsg(input_socket, mouse_data)
        prev_left_state = left

    # Only send right click events when state changes
    if right != prev_right_state:
        mouse_data = {
            'type': 'click',
            'button': 'right',
            'action': 'press' if right else 'release'
        }
        sendmsg(input_socket, mouse_data)
        prev_right_state = right


# Initialize Pygame
pygame.init()
screen = None


prev_left_state = False
prev_right_state = False


# Start keyboard listener
keyboard_listener = Listener(on_press=on_press, on_release=on_release)
keyboard_listener.start()

try:
    while True:
        # Receive screen data
        frame_size_data = recvall(screen_socket, 4)
        if not frame_size_data:
            break

        frame_size = struct.unpack(">L", frame_size_data)[0]
        data = recvall(screen_socket, frame_size)

        if data:
            image_stream = io.BytesIO(data)
            image = Image.open(image_stream)

            if screen is None:
                screen = pygame.display.set_mode(image.size)
                pygame.display.set_caption("Remote Control - Controller View")

            frame = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
            screen.blit(frame, (0, 0))
            pygame.display.flip()

        # Handle mouse input
        handle_mouse()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keyboard_listener.stop()
                screen_socket.close()
                input_socket.close()
                pygame.quit()
                exit()

except Exception as e:
    print(f"Error: {e}")
finally:
    keyboard_listener.stop()
    pygame.quit()
    screen_socket.close()
    input_socket.close()
