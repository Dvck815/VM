import requests
import tkinter as tk
from PIL import Image, ImageTk
from io import BytesIO
import threading
import sys

# URL of the browser running in the cloud VM
DEFAULT_URL = "https://lp2z0h7b-5000.use.devtunnels.ms"

class BrowserClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser Viewer")
        self.root.geometry("1024x768")
        
        # URL Input Frame
        url_frame = tk.Frame(root)
        url_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Label(url_frame, text="Server URL:").pack(side=tk.LEFT)
        self.url_entry = tk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.insert(0, DEFAULT_URL)
        
        connect_btn = tk.Button(url_frame, text="Update/Retry", command=self.reset_connection)
        connect_btn.pack(side=tk.LEFT)

        self.status_label = tk.Label(root, text="Connecting...", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.image_label = tk.Label(root)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        self.running = True
        self.target_url = DEFAULT_URL
        self.update_image()

    def reset_connection(self):
        url = self.url_entry.get().strip()
        # Auto-append /snapshot if user forgot it
        if not url.endswith('/snapshot'):
            url = url.rstrip('/') + '/snapshot'
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
            
        self.target_url = url
        self.status_label.config(text=f"Switched to {self.target_url}")

    def update_image(self):
        if not self.running:
            return
            
        try:
            # Use the URL from the entry box or default
            # Timeout increased to 5 seconds to handle network latency
            response = requests.get(self.target_url, timeout=5.0) 
            if response.status_code == 200:
                # Load image from content
                image_data = BytesIO(response.content)
                pil_image = Image.open(image_data)
                
                # Resize if necessary to fit window (optional, keeping original size for now)
                self.tk_image = ImageTk.PhotoImage(pil_image)
                
                self.image_label.config(image=self.tk_image)
                self.status_label.config(text=f"Connected to {self.target_url} - Live")
            else:
                self.status_label.config(text=f"Server returned {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.status_label.config(text=f"Connection lost to {self.target_url}... Retrying")
        except Exception as e:
            print(f"Error: {e}")
            self.status_label.config(text=f"Error: {str(e)}")
        
        # Schedule next update in 200ms
        self.root.after(200, self.update_image)

    def on_closing(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        client = BrowserClient(root)
        root.protocol("WM_DELETE_WINDOW", client.on_closing)
        root.mainloop()
    except ImportError as e:
        print("Error: Missing dependencies.")
        print(f"Details: {e}")
        print("Please run: pip install -r client_requirements.txt")
        input("Press Enter to exit...")
