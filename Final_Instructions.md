# Remote Chrome via VNC

This setup allows you to run a full Google Chrome desktop instance inside GitHub Codespaces and view/control it from your local browser.

## Quick Start

We have configured `localtunnel` as requested. 
**Note:** LocalTunnel enforces a password policy. We automatically fetch this password for you.

1. **Run the master script:**
   ```bash
   bash start_everything.sh
   ```

2. **Wait for Start:**
   The script will display two important things:
   - A **URL** (ends in `.loca.lt`)
   - A **Password** (Usually an IP address)

3. **Connect:**
   - Click the URL.
   - **Enter the Password** shown in the terminal.
   - Click "Submit".
   - Click the link to `vnc.html` (or add `/vnc.html` to the URL).
   - Click **Connect**.

## Troubleshooting

- **Stopping:** Press `Ctrl+C` in the terminal to stop all processes.
- **Force Cleanup:** If you encounter issues or processes get stuck, run the helper script:
  ```bash
  bash stop.sh
  ```
