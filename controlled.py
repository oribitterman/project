import socket
import mss
import cv2
import numpy as np
import struct
import time
import threading
import json
import os
import sys
from threading import Event, Thread

# For actual keyboard and mouse control
import pyautogui

# Server address - configurable via environment variables
SERVER_HOST = os.getenv('SERVER_HOST', '192.168.0.254')
SCREEN_PORT = int(os.getenv('SCREEN_PORT', '12345'))
INPUT_PORT = int(os.getenv('INPUT_PORT', '12346'))

# Configuration
QUALITY = 60  # JPEG quality
SCALE_FACTOR = 1.0  # Scale factor for screen capture
FRAME_RATE = 10  # Target frames per second

# Initialize pyautogui safely
pyautogui.FAILSAFE = False  # Disable fail-safe (move mouse to corner to abort)


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
    if data is None:
        return None
    try:
        key_data = json.loads(data.decode())
        return key_data
    except:
        return None


def recvall(sock, size):
    data = b''
    while len(data) < size:
        packet = sock.recv(min(size - len(data), 4096))
        if not packet:
            return None
        data += packet
    return data


# Now actually control keyboard instead of just simulating
def handle_keyboard_input(key_data):
    """Handle keyboard input commands using pyautogui"""
    action = key_data.get('type')
    key = key_data.get('key')

    try:
        if action == 'press':
            print(f"Keyboard press: {key}")
            pyautogui.keyDown(key)
        elif action == 'release':
            print(f"Keyboard release: {key}")
            pyautogui.keyUp(key)
    except Exception as e:
        print(f"Error controlling keyboard: {e}")


# Now actually control mouse instead of just simulating
def handle_mouse_input(mouse_data, screen_width, screen_height):
    """Handle mouse input commands using pyautogui"""
    action = mouse_data.get('type')

    try:
        if action == 'move':
            # Convert normalized position (0.0-1.0) to actual pixel position
            x = int(mouse_data.get('x') * screen_width)
            y = int(mouse_data.get('y') * screen_height)
            print(f"Mouse moved to: {x}, {y}")
            pyautogui.moveTo(x, y)

        elif action == 'click':
            button = mouse_data.get('button')
            btn_action = mouse_data.get('action')

            if button == 'left':
                if btn_action == 'press':
                    print(f"Left mouse button pressed")
                    pyautogui.mouseDown(button='left')
                elif btn_action == 'release':
                    print(f"Left mouse button released")
                    pyautogui.mouseUp(button='left')

            elif button == 'right':
                if btn_action == 'press':
                    print(f"Right mouse button pressed")
                    pyautogui.mouseDown(button='right')
                elif btn_action == 'release':
                    print(f"Right mouse button released")
                    pyautogui.mouseUp(button='right')
    except Exception as e:
        print(f"Error controlling mouse: {e}")


def handle_input(input_socket, stop_event, screen_width, screen_height):
    """Handle input commands from controller client"""
    try:
        while not stop_event.is_set():
            try:
                key_data = recvmsg(input_socket)
                if not key_data:
                    time.sleep(0.01)
                    continue

                key_type = key_data.get('type')

                if key_type in ['press', 'release']:
                    handle_keyboard_input(key_data)
                elif key_type in ['move', 'click']:
                    handle_mouse_input(key_data, screen_width, screen_height)

            except Exception as e:
                print(f"Error handling input: {e}")
                if isinstance(e, ConnectionError):
                    break

    except Exception as e:
        print(f"Input handler thread error: {e}")
    finally:
        print("Input handler thread stopped")


def main():
    screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    stop_event = Event()
    input_thread = None

    try:
        print(f"Connecting to server at {SERVER_HOST}...")
        screen_socket.connect((SERVER_HOST, SCREEN_PORT))
        input_socket.connect((SERVER_HOST, INPUT_PORT))

        print("Connected to server successfully")
        sendmsg(screen_socket, 'controlled_screen')
        sendmsg(input_socket, 'controlled_input')

        # Get screen dimensions
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # Primary monitor
            screen_width, screen_height = monitor["width"], monitor["height"]

        # Send screen information to the controller
        screen_info = {
            'type': 'screen_info',
            'width': screen_width,
            'height': screen_height
        }
        sendmsg(screen_socket, screen_info)

        # Start input handler thread
        input_thread = Thread(target=handle_input, args=(input_socket, stop_event, screen_width, screen_height))
        input_thread.daemon = True
        input_thread.start()

        # Start screen capture loop
        with mss.mss() as sct:
            # Define capture area (entire primary monitor)
            monitor = sct.monitors[0]

            # Scale dimensions if needed
            capture_width = int(monitor["width"] * SCALE_FACTOR)
            capture_height = int(monitor["height"] * SCALE_FACTOR)

            print(f"Capturing screen at {capture_width}x{capture_height}")

            # Main screen capture loop
            frame_interval = 1.0 / FRAME_RATE
            last_frame_time = time.time()

            while True:
                # Throttle to target frame rate
                current_time = time.time()
                time_since_last_frame = current_time - last_frame_time
                if time_since_last_frame < frame_interval:
                    time.sleep(frame_interval - time_since_last_frame)

                try:
                    # Capture screen
                    img = np.array(sct.grab(monitor))

                    # Convert from BGRA to RGB with improved color accuracy
                    # Use OpenCV's color conversion with enhanced color correction
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)

                    # Enhance contrast and color saturation slightly (optional)
                    img = cv2.convertScaleAbs(img, alpha=1.1, beta=0)

                    # Scale if needed
                    if SCALE_FACTOR != 1.0:
                        img = cv2.resize(img, (capture_width, capture_height), interpolation=cv2.INTER_LANCZOS4)

                    # Compress as JPEG
                    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])

                    # Send frame size then frame data
                    frame_data = buffer.tobytes()
                    frame_size = len(frame_data)
                    screen_socket.sendall(struct.pack(">L", frame_size) + frame_data)

                    last_frame_time = time.time()

                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                    print(f"Connection error: {e}")
                    break
                except Exception as e:
                    print(f"Error capturing screen: {e}")
                    time.sleep(1)  # Wait before retrying on error

    except KeyboardInterrupt:
        print("Controlled client shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up resources
        stop_event.set()
        if input_thread and input_thread.is_alive():
            input_thread.join(timeout=1.0)

        screen_socket.close()
        input_socket.close()
        print("Controlled client shut down successfully")


if __name__ == "__main__":
    main()
