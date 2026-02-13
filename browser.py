from flask import Flask, send_file, request, Response, render_template
import sys
import threading
import queue
from io import BytesIO

from PyQt6.QtCore import QUrl, QTimer, QBuffer, QIODevice, Qt, QPoint, QPointF, QEvent
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit, 
                             QPushButton, QVBoxLayout, QWidget)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction, QIcon, QMouseEvent, QKeyEvent

# --- Flask Server Setup ---
latest_screenshot_bytes = None
screenshot_lock = threading.Lock()
command_queue = queue.Queue()

flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return render_template('index.html')

def generate_mjpeg():
    """Generator for MJPEG stream."""
    while True:
        with screenshot_lock:
            data = latest_screenshot_bytes
        
        if data:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
        
        # Limit server-side FPS
        import time
        time.sleep(0.1)

@flask_app.route('/stream.mjpeg')
def stream():
    return Response(generate_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@flask_app.route('/click', methods=['GET', 'POST'])
def click():
    try:
        x = int(request.args.get('x'))
        y = int(request.args.get('y'))
        command_queue.put(('click', x, y))
        return "Clicked", 200
    except Exception as e:
        return str(e), 400

@flask_app.route('/type', methods=['GET', 'POST'])
def type_key():
    try:
        key = request.args.get('key')
        command_queue.put(('type', key))
        return "Typed", 200
    except Exception as e:
        return str(e), 400

@flask_app.route('/navigate', methods=['GET', 'POST'])
def navigate():
    try:
        url = request.args.get('url')
        command_queue.put(('navigate', url))
        return "Navigating", 200
    except Exception as e:
        return str(e), 400

def run_server():
    flask_app.run(port=5000, host='0.0.0.0', debug=False, use_reloader=False)

# --------------------------

class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Quick Browser")
        self.setGeometry(100, 100, 1024, 768)

        # Create the web engine view
        self.browser = QWebEngineView()
        
        import os
        self.browser.setUrl(QUrl("https://www.google.com"))
        
        # Connect urlChanged signal
        self.browser.urlChanged.connect(self.update_url_bar)
        
        # Set the central widget
        self.setCentralWidget(self.browser)

        # URL Bar Helper (Hidden logic)
        self.url_tracker = ""

        # Start Screenshot Timer - FASTER for video
        self.timer = QTimer()
        self.timer.timeout.connect(self.capture_screen)
        self.timer.start(100) # Capture every 100ms (10 FPS)

        # Start Command Processing
        self.cmd_timer = QTimer()
        self.cmd_timer.timeout.connect(self.process_commands)
        self.cmd_timer.start(50)

        # Start Server Thread
        print("Starting Flask Server...")
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    def process_commands(self):
        try:
            while not command_queue.empty():
                cmd, *args = command_queue.get_nowait()
                if cmd == 'navigate':
                    url = args[0]
                    if not url.startswith('http'):
                        url = 'https://' + url
                    self.browser.setUrl(QUrl(url))
                
                elif cmd == 'click':
                    x, y = args
                    pt = QPointF(float(x), float(y))
                    
                    target = self.browser.focusProxy()
                    if not target:
                        target = self.browser
                    
                    # PyQt6 QMouseEvent constructor requires careful argument matching
                    # (type, localPos, globalPos, button, buttons, modifiers)
                    
                    event_press = QMouseEvent(
                        QEvent.Type.MouseButtonPress, 
                        pt, 
                        pt, # globalPos (using local is often fine for single window)
                        Qt.MouseButton.LeftButton, 
                        Qt.MouseButton.LeftButton, 
                        Qt.KeyboardModifier.NoModifier
                    )
                    QApplication.sendEvent(target, event_press)
                    
                    event_release = QMouseEvent(
                        QEvent.Type.MouseButtonRelease, 
                        pt, 
                        pt,
                        Qt.MouseButton.LeftButton, 
                        Qt.MouseButton.LeftButton, 
                        Qt.KeyboardModifier.NoModifier
                    )
                    QApplication.sendEvent(target, event_release)
                
                elif cmd == 'type':
                    key_str = args[0]
                    # Simplified key injection
                    # You might need a more robust mapping for complex keys
                    key_code = 0
                    if len(key_str) == 1:
                        key_code = ord(key_str.upper())
                    
                    if key_str == 'Enter': key_code = Qt.Key.Key_Return
                    if key_str == 'Backspace': key_code = Qt.Key.Key_Backspace

                    target = self.browser.focusProxy()
                    if not target: target = self.browser

                    event = QKeyEvent(QEvent.Type.KeyPress, key_code, Qt.KeyboardModifier.NoModifier, key_str)
                    QApplication.sendEvent(target, event)
                    
                    event = QKeyEvent(QEvent.Type.KeyRelease, key_code, Qt.KeyboardModifier.NoModifier, key_str)
                    QApplication.sendEvent(target, event)


        except queue.Empty:
            pass

    def capture_screen(self):
        # Capture strictly the browser Viewport (web content)
        pixmap = self.browser.grab()
        
        # Save to JPG (Lower quality to 30 for speed/latency)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        pixmap.save(buffer, "JPG", quality=30)
        
        data = buffer.data().data()
        
        global latest_screenshot_bytes
        with screenshot_lock:
            latest_screenshot_bytes = data
            
    def update_url_bar(self, q):
        self.url_tracker = q.toString()

if __name__ == "__main__":
    import os
    # FORCE Software Rendering aggressively
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_XCB_FORCE_SOFTWARE_OPENGL"] = "1"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1" 
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QT_API"] = "pyqt6"
    
    qt_args = sys.argv + [
        "--no-sandbox", 
        "--disable-gpu", 
        "--disable-software-rasterizer", # sometimes helps? No, we want software.
        "--disable-dev-shm-usage",
        "--single-process",
        "--remote-debugging-port=9222"
    ]
    
    app = QApplication(qt_args)
    window = WebBrowser()
    window.show() # Must show to render, even in headless env (xvfb handles it)
    sys.exit(app.exec())
