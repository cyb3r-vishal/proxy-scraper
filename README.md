# ProxyScraper CLI + 24/7 Telegram Bot

A fast CLI tool that scrapes free proxies from **50+ sources**, validates them with **strict multi-endpoint checks** (100% live), and sends the results to your **Telegram bot** automatically.

Designed to run **24/7 on a Linux VPS** as a systemd service.

Created by **cyb3r_vishal** | community DevKitX

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

- **50+ Sources** ` Scrapes HTTP, HTTPS, SOCKS4, SOCKS5 from APIs, GitHub lists, and web tables
- **100% Live Validation** ` Every proxy tested against 3+ endpoints; must pass ALL checks
- **Telegram Integration** ` Auto-sends live proxies as .txt files to your Telegram chat
- **24/7 Daemon Mode** ` Runs on schedule (every 6h), restarts on crash, systemd service
- **Fast Async** ` Port pre-filter + concurrent validation (100 parallel checks)
- **Zero Bloat** ` 5 Python files, 3 dependencies, pure CLI

---

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run manually (scrape + validate HTTP)
python main.py -p http

# 3. Other protocols
python main.py -p socks5
python main.py -p https --json

# 4. Show all sources
python main.py --list-sources
```

## Telegram Bot Setup

1. Message **@BotFather** on Telegram` /newbot ` follow prompts ` copy the token
2. Message **@userinfobot** to get your chat ID
3. Create a `.env` file:

```bash
cp .env.example .env
nano .env
# Fill in:
# TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
# TELEGRAM_CHAT_ID=987654321
```

4. Test locally:

```bash
python daemon.py --once --types http
```

---

## Deploy on Linux VPS (24/7)

### Option 1: Auto Deploy Script

```bash
# Upload project to your VPS, then:
cd /path/to/proxy-scraper
chmod +x deploy.sh
sudo bash deploy.sh
```

The script will:
- Install Python + venv + dependencies
- Ask for your Telegram credentials
- Install and start the systemd service
- The bot runs 24/7 and auto-restarts on crash

### Option 2: Manual Setup

```bash
# 1. Clone/upload to VPS
cd /opt/proxy-scraper

# 2. Create venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env   # Add your Telegram token + chat ID

# 4. Install service
sudo cp proxyscraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable proxyscraper
sudo systemctl start proxyscraper

# 5. Check status
sudo systemctl status proxyscraper
journalctl -u proxyscraper -f
```

---

## Usage

### CLI (one-time scan)

```
python main.py [-p PROTO] [-o OUTPUT] [-i INPUT] [-t TIMEOUT] [-j] [-q]

Options:
  -p, --proto     Protocol: http, https, socks4, socks5 (default: http)
  -o, --output    Output file (default: output/<proto>_live.txt)
  -i, --input     Input file to validate (skips scraping)
  -t, --timeout   Timeout per check in seconds (default: 6)
  -j, --json      Also save detailed JSON report
  --list-sources  Show all scraping sources
  -q, --quiet     Minimal output
```

### Daemon (24/7 + Telegram)

```
python daemon.py [--types TYPE...] [--interval HOURS] [--target N] [--once]

Options:
  --types         Proxy types (default: http https socks4 socks5)
  --interval      Hours between cycles (default: 6)
  --target        Target live proxies per type (default: 1000)
  --timeout       Timeout per check (default: 6)
  --once          Run one cycle and exit
```

### Service Management

```bash
sudo systemctl status proxyscraper    # Check status
sudo systemctl restart proxyscraper   # Restart
sudo systemctl stop proxyscraper      # Stop
journalctl -u proxyscraper -f         # Live logs
tail -f /opt/proxy-scraper/logs/daemon.log  # Log file
```

---

## How Validation Works

Every proxy must pass **ALL** checks to be included � no exceptions:

| Protocol | Validation |
|----------|-----------|
| HTTP | HTTP request through proxy to icanhazip.com, api.ipify.org, ip.me |
| HTTPS | Same + HTTPS request to https://api.ipify.org |
| SOCKS4 | SOCKS4 CONNECT handshake to 3 different servers |
| SOCKS5 | SOCKS5 CONNECT handshake to 3 different servers |

**Pipeline:** Port check (2s) ` Endpoint 1 ` Endpoint 2 ` Endpoint 3 ` PASS/FAIL

If **any single check fails**, the proxy is discarded immediately.

---

## Project Structure

```
proxy-scraper/
+-- main.py               # CLI entry point (manual scans)
+-- daemon.py              # 24/7 daemon with Telegram integration
+-- scraper.py             # Async scraper (50+ sources)
+-- checker.py             # Strict multi-endpoint validator
+-- telegram_bot.py        # Telegram file sender
+-- requirements.txt       # httpx, beautifulsoup4, rich
+-- .env.example           # Template for Telegram credentials
+-- deploy.sh              # One-click VPS deployment
+-- proxyscraper.service   # systemd service file
+-- output/                # Generated proxy files
+-- logs/                  # Daemon logs
```

## License

MIT
