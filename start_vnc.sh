#!/bin/bash
export DISPLAY=:1
export MOZ_FAKE_NO_SANDBOX=1

# 1. Start Xvfb (Virtual Screen)
Xvfb :1 -screen 0 1280x720x24 &
XPID=$!
sleep 2

# 2. Start Window Manager
fluxbox &

# 3. Start VNC Server (No password for easy access, listens on localhost)
x11vnc -display :1 -forever -nopw -shared -bg

# 4. Start noVNC (Web Bridge)
# Use the installed websockify to wrap 5900 -> 6080
websockify --web /usr/share/novnc 6080 localhost:5900 &
PID_WEB=$!

# 5. Start Chrome
# Flags needed for container environment
google-chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-port=9222 --start-maximized https://www.google.com &

echo "VNC Server running."
echo "Press Ctrl+C to stop."

wait $XPID
