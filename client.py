import socket
import sys
import json
import struct
import threading
import time
import os

# Server address - configurable via environment variables
SERVER_HOST = os.getenv('SERVER_HOST', '192.168.0.254')
SCREEN_PORT = int(os.getenv('SCREEN_PORT', '12345'))
INPUT_PORT = int(os.getenv('INPUT_PORT', '12346'))

def main():
    # Automatically start in controller mode with fullscreen
    choice = 0  # Always start as controllerhhhhhh

    try:
        if choice == 1:
            print("Starting as Controller...")
            import controller
            controller.main()
        else:
            print("Starting as Controlled...")
            import controlled
            controlled.main()
    except ModuleNotFoundError:
        print("Error: Could not find the required modules.")
        print("Make sure controller.py and controlled.py are in the same directory as client.py.")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Make sure all required libraries are installed.")
        print("You may need to run: pip install mss opencv-python keyboard mouse pygame Pillow numpy")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
    except Exception as e:
        print(f"Unexpected error in main program: {e}")