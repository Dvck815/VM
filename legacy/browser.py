import sys
import threading
import queue
from io import BytesIO
from flask import Flask, send_file, request

from PyQt6.QtCore import QUrl, QTimer, QBuffer, QIODevice, Qt, QPoint, QEvent
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit, 
                             QPushButton, QVBoxLayout, QWidget)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QAction, QIcon, QMouseEvent

# --- Flask Server Setup ---
latest_screenshot_data = None
screenshot_lock = threading.Lock()
command_queue = queue.Queue()

flask_app = Flask(__name__)

@flask_app.route('/snapshot')
def snapshot():
    with screenshot_lock:
        if latest_screenshot_data:
            return send_file(BytesIO(latest_screenshot_data), mimetype='image/png')
        else:
            return "No image yet", 404

@flask_app.route('/click', methods=['GET', 'POST'])
def click():
    try:
        x = int(request.args.get('x'))
        y = int(request.args.get('y'))
        command_queue.put(('click', x, y))
        return "Clicked", 200
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
        
        # Load local test file first to verify rendering
        import os
        local_url = QUrl.fromLocalFile(os.path.abspath("test.html"))
        self.browser.setUrl(local_url)
        # self.browser.setUrl(QUrl("https://www.google.com"))
        
        # Connect urlChanged signal to update the address bar
        self.browser.urlChanged.connect(self.update_url_bar)
        
        # Debugging signals
        self.browser.loadStarted.connect(lambda: print("Page load started..."))
        self.browser.loadProgress.connect(lambda p: print(f"Loading progress: {p}%"))
        self.browser.loadFinished.connect(lambda ok: print(f"Page loaded successfully: {ok}"))

        # Set the central widget
        self.setCentralWidget(self.browser)

        # Create a navigation toolbar
        navbar = QToolBar()
        self.addToolBar(navbar)

        # Back Button
        back_btn = QAction("Back", self)
        back_btn.setStatusTip("Back to previous page")
        back_btn.triggered.connect(self.browser.back)
        navbar.addAction(back_btn)

        # Forward Button
        forward_btn = QAction("Forward", self)
        forward_btn.setStatusTip("Forward to next page")
        forward_btn.triggered.connect(self.browser.forward)
        navbar.addAction(forward_btn)

        # Reload Button
        reload_btn = QAction("Reload", self)
        reload_btn.setStatusTip("Reload page")
        reload_btn.triggered.connect(self.browser.reload)
        navbar.addAction(reload_btn)

        # Home Button
        home_btn = QAction("Home", self)
        home_btn.setStatusTip("Go home")
        home_btn.triggered.connect(self.navigate_home)
        navbar.addAction(home_btn)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)

        # Update URL initially
        self.update_url_bar(self.browser.url())

        # Start Screenshot Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.capture_screen)
        self.timer.start(1000) # Capture every second

        # Start Command Processing Timer (Check queue every 50ms)
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
                    self.url_bar.setText(url)
                elif cmd == 'click':
                    x, y = args
                    # Adjust for toolbar height (rough estimate 30-40px)
                    # Coordinates come in relative to the window content area (image)
                    # We need to target the browser widget specifically
                    
                    # Map window coordinates to browser widget coordinates?
                    # The image capture is self.browser.grab(), so coordinates should match browser widget exactly!
                    # BUT self.browser is the central widget.
                    
                    # Create Qt Mouse Events
                    # Press
                    pt = QPoint(x, y)
                    event_press = QMouseEvent(QEvent.Type.MouseButtonPress, pt, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(self.browser, event_press)
                    
                    # Release
                    event_release = QMouseEvent(QEvent.Type.MouseButtonRelease, pt, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(self.browser, event_release)
                    
                    print(f"Simulated click at {x}, {y}")
        except queue.Empty:
            pass

    def capture_screen(self):
        # Grab the screenshot of the browser widget
        pixmap = self.browser.grab()
        
        # Save to bytes
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        pixmap.save(buffer, "PNG")
        
        data = buffer.data().data()
        
        global latest_screenshot_data
        with screenshot_lock:
            latest_screenshot_data = data

    def navigate_home(self):
        self.browser.setUrl(QUrl("https://www.google.com"))

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith('http'):
            url = 'https://' + url
        self.browser.setUrl(QUrl(url))

    def update_url_bar(self, q):
        self.url_bar.setText(q.toString())

if __name__ == "__main__":
    import os
    # FORCE Software Rendering for Qt Quick/WebEngine
    # os.environ["QT_QUICK_BACKEND"] = "software" # allow auto-detect
    os.environ["QT_XCB_FORCE_SOFTWARE_OPENGL"] = "1"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1" 
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    
    # Add arguments to fix rendering in containers
    qt_args = sys.argv + [
        "--no-sandbox", 
        "--disable-gpu", 
        "--disable-dev-shm-usage",
        "--single-process" 
    ]
    
    app = QApplication(qt_args)
    app.setApplicationName("Chromium Browser")
    
    window = WebBrowser()
    window.show()
    
    sys.exit(app.exec())
