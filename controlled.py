# controlled.py
import socket
import mss
import cv2
import numpy as np
import struct
import time
import threading
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import json

# Server address
SERVER_HOST = '192.168.0.194'
SCREEN_PORT = 12345
INPUT_PORT = 12346


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

# Initialize controllers
keyboard = KeyboardController()
mouse = MouseController()

# Create two sockets
screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect both sockets
screen_socket.connect((SERVER_HOST, SCREEN_PORT))
input_socket.connect((SERVER_HOST, INPUT_PORT))

sendmsg(screen_socket, 'controlled_screen')
sendmsg(input_socket, 'controlled_input')

def recvall(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(min(size - len(data), 4096))
        if not packet:
            return None
        data += packet
    return data


def handle_input():
    while True:
        #try:
            # Receive keyboard input data
            key_data = recvmsg(input_socket)
            if key_data:
                print(key_data['type'])
                if key_data['type']=='press'  or key_data['type']=='release':
                    handle_keyboard_input(key_data)
                if key_data['type'] == 'move' or key_data['type'] == 'click':
                    handle_mouse_input(key_data)
        #except Exception as e:
        #    print(f"Error handling keyboard input: {e}")
        #    continue

def handle_keyboard_input(key_data):
    key = key_data['key']

    # Map special keys
    special_keys = {
        'Key.space': Key.space,
        'Key.enter': Key.enter,
        'Key.backspace': Key.backspace,
        'Key.tab': Key.tab,
        'Key.shift': Key.shift,
        'Key.ctrl': Key.ctrl,
        'Key.alt': Key.alt,
        'Key.caps_lock': Key.caps_lock,
        'Key.esc': Key.esc,
        'Key.delete': Key.delete,
        'Key.up': Key.up,
        'Key.down': Key.down,
        'Key.left': Key.left,
        'Key.right': Key.right,
    }

    if key in special_keys:
        if key_data['type'] == 'press':
            keyboard.press(special_keys[key])
        else:
            keyboard.release(special_keys[key])
    else:
        key = key.strip("'")
        if key_data['type'] == 'press':
            keyboard.press(key)
        else:
            keyboard.release(key)


def handle_mouse_input(mouse_data):
    if mouse_data['type'] == 'move':
        with mss.mss() as sct:
            screen_width = sct.monitors[1]['width']
            screen_height = sct.monitors[1]['height']

        x = mouse_data['x'] * screen_width
        y = mouse_data['y'] * screen_height
        mouse.position = (x, y)

    elif mouse_data['type'] == 'click':
        button = mouse_data['button']
        if button == 'left':
            button = Button.left
        elif button == 'right':
            button = Button.right

        if mouse_data['action'] == 'press':
            mouse.press(button)
        elif mouse_data['action'] == 'release':
            mouse.release(button)



# Start input handler threads
input_thread = threading.Thread(target=handle_input, daemon=True)
input_thread.start()

# Screen capturing setup
with mss.mss() as sct:
    monitor = sct.monitors[1]
    target_fps = 10
    target_interval = 1 / target_fps
    last_frame_time = time.time()

    try:
        while True:
            current_time = time.time()
            if current_time - last_frame_time >= target_interval:
                last_frame_time = current_time
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                success, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])

                if success:
                    data = encoded_frame.tobytes()
                    size = len(data)
                    screen_socket.sendall(struct.pack(">L", size) + data)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        screen_socket.close()
        input_socket.close()
