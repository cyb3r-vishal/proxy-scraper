#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# ProxyScraper VPS Deploy Script
# Run this on your Linux VPS to set everything up
# Usage: curl -sSL <url> | bash   OR   bash deploy.sh
# ──────────────────────────────────────────────────────────────────────

set -e

INSTALL_DIR="/opt/proxy-scraper"
SERVICE_NAME="proxyscraper"
PYTHON_MIN="3.10"

echo "============================================"
echo "  ProxyScraper — VPS Deployment"
echo "  by cyb3r_vishal | community DevKitX"
echo "============================================"
echo ""

# ── Check Python version ────────────────────────────────────────────
echo "[1/6] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "  Python3 not found. Installing..."
    apt update && apt install -y python3 python3-pip python3-venv
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python $PYTHON_VER found"

# ── Create install directory ────────────────────────────────────────
echo "[2/6] Setting up $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -f scraper.py checker.py main.py daemon.py telegram_bot.py requirements.txt "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/output" "$INSTALL_DIR/logs"

# ── Create virtual environment ──────────────────────────────────────
echo "[3/6] Creating virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "  Dependencies installed"

# ── Configure .env ──────────────────────────────────────────────────
echo "[4/6] Configuring Telegram..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    read -p "  Enter Telegram Bot Token (from @BotFather): " BOT_TOKEN
    read -p "  Enter Telegram Chat ID: " CHAT_ID
    
    cat > "$INSTALL_DIR/.env" <<EOF
# ProxyScraper Configuration
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_CHAT_ID=$CHAT_ID
EOF
    echo "  .env created"
else
    echo "  .env already exists, skipping"
fi

# ── Install systemd service ─────────────────────────────────────────
echo "[5/6] Installing systemd service..."
cp -f proxyscraper.service /etc/systemd/system/ 2>/dev/null || \
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=ProxyScraper Daemon — 24/7 proxy scraper & validator with Telegram
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python daemon.py --interval 6 --target 1000
Restart=always
RestartSec=30
StandardOutput=append:$INSTALL_DIR/logs/daemon.log
StandardError=append:$INSTALL_DIR/logs/daemon.log
EnvironmentFile=$INSTALL_DIR/.env
LimitNOFILE=65535
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# ── Verify ──────────────────────────────────────────────────────────
echo "[6/6] Verifying..."
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "============================================"
    echo "  ✅ ProxyScraper is running!"
    echo "============================================"
    echo ""
    echo "  Service:  systemctl status $SERVICE_NAME"
    echo "  Logs:     journalctl -u $SERVICE_NAME -f"
    echo "  Log file: tail -f $INSTALL_DIR/logs/daemon.log"
    echo "  Stop:     systemctl stop $SERVICE_NAME"
    echo "  Restart:  systemctl restart $SERVICE_NAME"
    echo "  Config:   nano $INSTALL_DIR/.env"
    echo ""
    echo "  The bot will scrape & validate proxies every 6 hours"
    echo "  and send live proxies as .txt files to your Telegram."
    echo ""
else
    echo ""
    echo "  ⚠️  Service may not have started. Check:"
    echo "  journalctl -u $SERVICE_NAME -n 50"
    echo ""
fi
