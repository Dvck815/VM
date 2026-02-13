#!/bin/bash

# Master Setup & Startup Script
# - Installs dependencies
# - Starts VNC/Chrome
# - Exposes via LocalTunnel (requested)
# - Fetches the required password automatically

set -m

cleanup() {
    echo ""
    echo ">>> Shutting down..."
    kill -TERM -$$ 2>/dev/null
}
trap cleanup SIGINT SIGTERM EXIT

echo ">>> Checking Dependencies..."

# 1. System Tools
if ! command -v websockify &> /dev/null || ! command -v Xvfb &> /dev/null; then
    echo "Installing VNC tools..."
    sudo apt-get update
    # Install XFCE4 instead of fluxbox
    sudo apt-get install -y xfce4 xfce4-terminal x11vnc novnc websockify net-tools xvfb dbus-x11
fi

# 2. Chrome
if ! command -v google-chrome &> /dev/null; then
    echo "Installing Google Chrome..."
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y ./google-chrome-stable_current_amd64.deb
    rm google-chrome-stable_current_amd64.deb
fi

# 3. LocalTunnel (npm)
if ! command -v lt &> /dev/null; then
    echo "Installing LocalTunnel..."
    sudo npm install -g localtunnel
fi

echo ">>> Starting Environment..."

# Clean locks
rm -f /tmp/.X1-lock
pkill -f "Xvfb :1" 2>/dev/null

# Start Xvfb (24-bit color - Standard)
export DISPLAY=:1
Xvfb :1 -screen 0 1280x720x24 > /dev/null 2>&1 &
XPID=$!
sleep 2

# Start XFCE4 & VNC
# fluxbox -display :1 > /dev/null 2>&1 &
# startxfce4 automatically uses the DISPLAY env var
startxfce4 > /dev/null 2>&1 &
x11vnc -display :1 -forever -nopw -shared -bg -quiet

# Start Websockify
websockify --web /usr/share/novnc 6080 localhost:5900 > /dev/null 2>&1 &
PID_WEB=$!

# Chrome auto-start removed for Desktop experience
# google-chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --start-maximized --no-first-run --no-default-browser-check https://www.google.com &

echo ">>> Starting Tunnel (localtunnel)..."
rm -f tunnel.log
# Start lt/localtunnel
lt --port 6080 > tunnel.log 2>&1 &
CPID=$!

echo "Waiting for tunnel..."
sleep 5

# Extract URL and Password
URL=$(grep "your url is:" tunnel.log | sed 's/your url is: //')
# Password (IP) is REQUIRED by LocalTunnel
PASSWORD=$(curl -s https://loca.lt/mytunnelpassword)

if [ -z "$URL" ]; then
    echo "Error: Could not get tunnel URL. Retrying..."
    sleep 5
    URL=$(grep "your url is:" tunnel.log | sed 's/your url is: //')
fi

echo ""
echo "======================================================="
echo "   REMOTE DESKTOP READY"
echo "======================================================="
echo ""
echo "1. URL (Click this):"
echo "   $URL/vnc.html"
echo ""
echo "2. PASSWORD (REQUIRED):"
echo "   $PASSWORD"
echo ""
echo "NOTE: LocalTunnel REQUIRES this password to connect."
echo "      We cannot remove it, but we fetched it for you!"
echo "======================================================="
echo "Press Ctrl+C to stop."

wait $XPID
