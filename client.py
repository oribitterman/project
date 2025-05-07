import socket
import sys
import json
import struct
import threading
import time
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font

# Server address - configurable via environment variables
SERVER_HOST = os.getenv('SERVER_HOST', '192.168.0.188')
SCREEN_PORT = int(os.getenv('SCREEN_PORT', '12345'))
INPUT_PORT = int(os.getenv('INPUT_PORT', '12346'))


class RemoteControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Control System")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Set application icon if available
        try:
            self.root.iconbitmap("icon.ico")  # Replace with your icon if you have one
        except:
            pass

        # Configure style
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TButton", font=("Arial", 12))
        self.style.configure("TLabel", font=("Arial", 12), background="#f0f0f0")
        self.style.configure("Header.TLabel", font=("Arial", 18, "bold"), background="#f0f0f0")

        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create header
        header_label = ttk.Label(self.main_frame, text="Remote Control System", style="Header.TLabel")
        header_label.pack(pady=(20, 30))

        # Create description
        description = ttk.Label(self.main_frame,
                                text="Choose a mode to start the application:",
                                wraplength=400)
        description.pack(pady=(0, 20))

        # Create mode selection frame
        mode_frame = ttk.Frame(self.main_frame)
        mode_frame.pack(pady=20, fill=tk.X)

        # Controller button
        controller_btn = ttk.Button(mode_frame, text="Controller",
                                    width=20,
                                    command=self.start_controller)
        controller_btn.pack(side=tk.LEFT, padx=(40, 20))

        # Controlled button
        controlled_btn = ttk.Button(mode_frame, text="Controlled",
                                    width=20,
                                    command=self.start_controlled)
        controlled_btn.pack(side=tk.RIGHT, padx=(20, 40))

        # Add descriptions for each mode
        controller_desc = ttk.Label(self.main_frame,
                                    text="Control another computer",
                                    wraplength=200)
        controller_desc.pack(pady=(10, 0))

        controlled_desc = ttk.Label(self.main_frame,
                                    text="Allow your computer to be controlled",
                                    wraplength=400)
        controlled_desc.pack(pady=(10, 0))

        # Server info
        server_frame = ttk.Frame(self.main_frame)
        server_frame.pack(side=tk.BOTTOM, pady=20, fill=tk.X)

        server_label = ttk.Label(server_frame,
                                 text=f"Server: {SERVER_HOST}:{SCREEN_PORT}/{INPUT_PORT}",
                                 font=("Arial", 10))
        server_label.pack()

    def start_controller(self):
        self.root.destroy()  # Close the UI
        try:
            print("Starting as Controller...")
            import controller
            controller.main()
        except ModuleNotFoundError:
            messagebox.showerror("Error",
                                 "Could not find the required modules.\nMake sure controller.py is in the same directory as client.py.")
        except ImportError as e:
            messagebox.showerror("Error",
                                 f"Error importing modules: {e}\nMake sure all required libraries are installed.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def start_controlled(self):
        self.root.destroy()  # Close the UI
        try:
            print("Starting as Controlled...")
            import controlled
            controlled.main()
        except ModuleNotFoundError:
            messagebox.showerror("Error",
                                 "Could not find the required modules.\nMake sure controlled.py is in the same directory as client.py.")
        except ImportError as e:
            messagebox.showerror("Error",
                                 f"Error importing modules: {e}\nMake sure all required libraries are installed.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")


def main():
    root = tk.Tk()
    app = RemoteControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
    except Exception as e:
        print(f"Unexpected error in main program: {e}")
