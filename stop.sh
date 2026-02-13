#!/bin/bash

# Force Stop Script
# Run this if the main script is stuck or you want to restart cleanly.

echo ">>> Stopping all remote browser processes..."

# Kill specific processes by name pattern
pkill -f "start_everything.sh"
pkill -f "Xvfb :1"
pkill -f "x11vnc"
pkill -f "websockify"
pkill -f "chrome"
pkill -f "cloudflared tunnel"
pkill -f "lt --port"

# Wait a moment
sleep 1

# Force kill if anything remains
pkill -9 -f "Xvfb :1" 2>/dev/null
pkill -9 -f "chrome" 2>/dev/null

# Clean up lock files
rm -f /tmp/.X1-lock
rm -f tunnel.log

echo ">>> Done. Environment is clean."
