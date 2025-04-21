import socket
import pygame
import io
import struct
from PIL import Image
import json
import time
import os

# Server address - configurable via environment variables
SERVER_HOST = os.getenv('SERVER_HOST', '192.168.0.254')
SCREEN_PORT = int(os.getenv('SCREEN_PORT', '12345'))
INPUT_PORT = int(os.getenv('INPUT_PORT', '12346'))

# Global variables
screen = None
input_socket = None
screen_socket = None
fullscreen_mode = True  # Start in fullscreen mode by default
original_size = (1024, 768)  # Default windowed size
remote_width = 1920  # Default, will be updated from remote
remote_height = 1080  # Default, will be updated from remote
mouse_pressed = {"left": False, "right": False}  # Track mouse button state


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


# pygame key event to name mapping
def get_key_name(key):
    # Convert pygame key code to a name similar to what keyboard library would use
    key_mapping = {
        pygame.K_a: 'a', pygame.K_b: 'b', pygame.K_c: 'c', pygame.K_d: 'd',
        pygame.K_e: 'e', pygame.K_f: 'f', pygame.K_g: 'g', pygame.K_h: 'h',
        pygame.K_i: 'i', pygame.K_j: 'j', pygame.K_k: 'k', pygame.K_l: 'l',
        pygame.K_m: 'm', pygame.K_n: 'n', pygame.K_o: 'o', pygame.K_p: 'p',
        pygame.K_q: 'q', pygame.K_r: 'r', pygame.K_s: 's', pygame.K_t: 't',
        pygame.K_u: 'u', pygame.K_v: 'v', pygame.K_w: 'w', pygame.K_x: 'x',
        pygame.K_y: 'y', pygame.K_z: 'z',
        pygame.K_0: '0', pygame.K_1: '1', pygame.K_2: '2', pygame.K_3: '3',
        pygame.K_4: '4', pygame.K_5: '5', pygame.K_6: '6', pygame.K_7: '7',
        pygame.K_8: '8', pygame.K_9: '9',
        pygame.K_SPACE: 'space', pygame.K_TAB: 'tab', pygame.K_RETURN: 'enter',
        pygame.K_BACKSPACE: 'backspace', pygame.K_DELETE: 'delete',
        pygame.K_ESCAPE: 'esc', pygame.K_CAPSLOCK: 'caps lock',
        pygame.K_F1: 'f1', pygame.K_F2: 'f2', pygame.K_F3: 'f3', pygame.K_F4: 'f4',
        pygame.K_F5: 'f5', pygame.K_F6: 'f6', pygame.K_F7: 'f7', pygame.K_F8: 'f8',
        pygame.K_F9: 'f9', pygame.K_F10: 'f10', pygame.K_F11: 'f11', pygame.K_F12: 'f12',
        pygame.K_UP: 'up', pygame.K_DOWN: 'down', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right',
        pygame.K_LSHIFT: 'shift', pygame.K_RSHIFT: 'shift',
        pygame.K_LCTRL: 'ctrl', pygame.K_RCTRL: 'ctrl',
        pygame.K_LALT: 'alt', pygame.K_RALT: 'alt',
        pygame.K_SEMICOLON: ';', pygame.K_COMMA: ',', pygame.K_PERIOD: '.',
        pygame.K_SLASH: '/', pygame.K_BACKSLASH: '\\', pygame.K_MINUS: '-',
        pygame.K_EQUALS: '=', pygame.K_LEFTBRACKET: '[', pygame.K_RIGHTBRACKET: ']',
        pygame.K_QUOTE: "'",
        pygame.K_PAGEUP: 'page up', pygame.K_PAGEDOWN: 'page down',
        pygame.K_HOME: 'home', pygame.K_END: 'end', pygame.K_INSERT: 'insert',
        pygame.K_NUMLOCK: 'num lock', pygame.K_SCROLLOCK: 'scroll lock',
        pygame.K_PRINTSCREEN: 'print screen'
    }
    return key_mapping.get(key, str(key))


def handle_key_event(key, event_type):
    global fullscreen_mode, screen, input_socket

    key_name = get_key_name(key)

    # Handle special keys locally
    if event_type == 'press' and key_name == 'f11':
        toggle_fullscreen()
        return

    if event_type == 'press' and key_name == 'esc' and fullscreen_mode:
        toggle_fullscreen()
        return

    try:
        key_data = {
            'type': event_type,
            'key': key_name
        }
        sendmsg(input_socket, key_data)
    except Exception as e:
        print(f"Error sending key {event_type}: {e}")


def toggle_fullscreen():
    global fullscreen_mode, screen, original_size

    if screen is None:
        print("Screen not initialized yet")
        return

    current_w, current_h = screen.get_size()

    if fullscreen_mode:
        # Switch to windowed mode
        screen = pygame.display.set_mode(original_size)
        fullscreen_mode = False
        print("Switched to windowed mode")
    else:
        # Save current window size before going fullscreen
        original_size = (current_w, current_h)
        # Switch to fullscreen mode
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        fullscreen_mode = True
        print("Switched to fullscreen mode")

    pygame.display.flip()


def handle_mouse():
    global screen, remote_width, remote_height, mouse_pressed

    if screen is None or input_socket is None:
        return

    screen_width, screen_height = screen.get_size()
    x, y = pygame.mouse.get_pos()

    # Get the current display area dimensions (accounting for letterboxing)
    display_width, display_height, offset_x, offset_y = get_display_dimensions(screen_width, screen_height)

    # Check if mouse is in the display area
    if (offset_x <= x < offset_x + display_width and offset_y <= y < offset_y + display_height):
        # Normalize position within the display area (0.0 to 1.0)
        norm_x = (x - offset_x) / display_width
        norm_y = (y - offset_y) / display_height

        # Debug output
        # print(f"Mouse: {x},{y} -> Norm: {norm_x:.2f},{norm_y:.2f}")

        # Send normalized mouse position
        try:
            mouse_data = {
                'type': 'move',
                'x': norm_x,
                'y': norm_y
            }
            sendmsg(input_socket, mouse_data)
        except Exception as e:
            print(f"Error sending mouse position: {e}")

    # Get current mouse button state
    current_buttons = pygame.mouse.get_pressed()
    left_pressed = bool(current_buttons[0])
    right_pressed = bool(current_buttons[2])

    # Handle left mouse button
    if left_pressed != mouse_pressed["left"]:
        mouse_pressed["left"] = left_pressed

        # Send mouse click event
        try:
            mouse_data = {
                'type': 'click',
                'button': 'left',
                'action': 'press' if left_pressed else 'release'
            }
            sendmsg(input_socket, mouse_data)
        except Exception as e:
            print(f"Error sending left click: {e}")

    # Handle right mouse button
    if right_pressed != mouse_pressed["right"]:
        mouse_pressed["right"] = right_pressed

        # Send mouse click event
        try:
            mouse_data = {
                'type': 'click',
                'button': 'right',
                'action': 'press' if right_pressed else 'release'
            }
            sendmsg(input_socket, mouse_data)
        except Exception as e:
            print(f"Error sending right click: {e}")


def get_display_dimensions(screen_width, screen_height):
    """
    Calculate the dimensions of the display area, accounting for letterboxing
    Returns (display_width, display_height, offset_x, offset_y)
    """
    global remote_width, remote_height

    # Calculate aspect ratios
    screen_aspect = screen_width / screen_height
    remote_aspect = remote_width / remote_height

    if screen_aspect > remote_aspect:  # Screen is wider than remote
        # Height limited, width has black bars
        display_height = screen_height
        display_width = int(display_height * remote_aspect)
        offset_x = (screen_width - display_width) // 2
        offset_y = 0
    else:  # Screen is taller than remote
        # Width limited, height has black bars
        display_width = screen_width
        display_height = int(display_width / remote_aspect)
        offset_x = 0
        offset_y = (screen_height - display_height) // 2

    return display_width, display_height, offset_x, offset_y


def main():
    global screen, input_socket, screen_socket, remote_width, remote_height, original_size, fullscreen_mode

    screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    input_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"Connecting to server at {SERVER_HOST}...")
        screen_socket.connect((SERVER_HOST, SCREEN_PORT))
        input_socket.connect((SERVER_HOST, INPUT_PORT))

        print("Connected to server successfully")
        sendmsg(screen_socket, 'controller_screen')
        sendmsg(input_socket, 'controller_input')

        print("Waiting for a controlled client to connect...")

        pygame.init()
        pygame.display.init()

        # Initialize in fullscreen mode by default
        screen_info = pygame.display.Info()
        screen_width, screen_height = screen_info.current_w, screen_info.current_h

        if fullscreen_mode:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            screen = pygame.display.set_mode(original_size)

        pygame.display.set_caption("Remote Control - Waiting for Connection")

        # Display waiting message
        waiting_font = pygame.font.Font(None, 36)
        waiting_text = waiting_font.render("Waiting for a controlled client to connect...", True, (255, 255, 255))
        waiting_rect = waiting_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

        # Draw initial screen
        screen.fill((0, 0, 0))
        screen.blit(waiting_text, waiting_rect)
        pygame.display.flip()

        connection_active = False
        clock = pygame.time.Clock()

        while True:
            # Process all pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt("User closed the window")
                elif event.type == pygame.KEYDOWN:
                    # Handle key press events
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                    elif event.key == pygame.K_ESCAPE and fullscreen_mode:
                        toggle_fullscreen()
                    else:
                        # Forward other key presses to the controlled client
                        handle_key_event(event.key, 'press')
                elif event.type == pygame.KEYUP:
                    # Handle key release events
                    if event.key not in [pygame.K_F11, pygame.K_ESCAPE]:
                        # Forward key releases to controlled client
                        handle_key_event(event.key, 'release')

            # Always handle mouse for interaction with remote system
            if connection_active:
                handle_mouse()

            # Process incoming screen data
            try:
                # Try to receive frame size
                try:
                    frame_size_data = recvall(screen_socket, 4)
                    if not frame_size_data:
                        time.sleep(0.01)
                        continue
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                    print(f"Connection error: {e}")
                    break
                except Exception as e:
                    print(f"Error receiving frame size: {e}")
                    time.sleep(0.01)
                    continue

                frame_size = struct.unpack(">L", frame_size_data)[0]
                data = recvall(screen_socket, frame_size)

                if data:
                    try:
                        # Try to interpret data as JSON
                        message = json.loads(data.decode())
                        if isinstance(message, dict):
                            if message.get('type') == 'connection_status':
                                if message.get('status') == 'complete':
                                    print("Connection to controlled client established!")
                                    connection_active = True
                            elif message.get('type') == 'screen_info':
                                remote_width = message.get('width', 1920)
                                remote_height = message.get('height', 1080)

                                print(f"Remote screen size: {remote_width}x{remote_height}")

                                # If not already in fullscreen, update the window with the right aspect ratio
                                if not fullscreen_mode:
                                    # Calculate aspect ratio
                                    aspect_ratio = remote_width / remote_height

                                    # Determine new window size based on aspect ratio
                                    # but maintain same window area for similar pixel density
                                    current_area = original_size[0] * original_size[1]
                                    new_height = int((current_area / aspect_ratio) ** 0.5)
                                    new_width = int(new_height * aspect_ratio)

                                    # Update original size and recreate window
                                    original_size = (new_width, new_height)
                                    screen = pygame.display.set_mode(original_size)

                                pygame.display.set_caption(
                                    f"Remote Control - Controller View ({remote_width}x{remote_height})")
                                connection_active = True
                        continue
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Not JSON data, treat as image data
                        pass

                    try:
                        # Process image data
                        image_stream = io.BytesIO(data)
                        image = Image.open(image_stream)

                        # Get the current screen size
                        screen_width, screen_height = screen.get_size()

                        # Calculate display area dimensions and offsets (for letterboxing)
                        display_width, display_height, offset_x, offset_y = get_display_dimensions(
                            screen_width, screen_height)

                        # Resize image to the display area dimensions, preserving aspect ratio
                        image = image.resize((display_width, display_height), Image.LANCZOS)

                        # Convert to pygame surface
                        frame = pygame.image.fromstring(image.tobytes(), image.size, image.mode)

                        # Clear screen with black
                        screen.fill((0, 0, 0))

                        # Blit the image with calculated offsets to maintain aspect ratio
                        screen.blit(frame, (offset_x, offset_y))

                        # Update the display
                        pygame.display.flip()
                    except Exception as e:
                        print(f"Error processing image: {e}")
                        continue
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                print(f"Connection error: {e}")
                print("Server disconnected. Exiting...")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                continue

            # Limit to 60 FPS to prevent excessive CPU usage
            clock.tick(60)

    except KeyboardInterrupt:
        print("Controller shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up resources
        pygame.quit()
        try:
            screen_socket.close()
            input_socket.close()
        except:
            pass
        print("Controller shut down successfully")


if __name__ == "__main__":
    main()
