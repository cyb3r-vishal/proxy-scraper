# ProxyScraper CLI

A fast, clean CLI tool that scrapes free proxies from 30+ sources and validates them to ensure **100% live** results.

Created by **cyb3r_vishal** | community DevKitX

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **30+ Sources** — Scrapes HTTP, HTTPS, SOCKS4, SOCKS5 proxies from APIs, GitHub lists, and web tables
- **100% Live Validation** — Every proxy is tested against multiple endpoints; only proxies that pass ALL checks are kept
- **Fast Async** — Concurrent scraping and validation with 150 parallel checks
- **Clean Output** — Live proxies saved to text (and optional JSON with response times)
- **Zero Bloat** — 3 files, 3 dependencies, pure CLI

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape and validate HTTP proxies
python main.py

# SOCKS5 proxies
python main.py -p socks5

# Custom output file
python main.py -p https -o my_proxies.txt

# Validate proxies from an existing file
python main.py -i raw_proxies.txt -p http

# Save detailed JSON report
python main.py -p http --json

# Show all proxy sources
python main.py --list-sources
```

## Usage

```
usage: proxyscraper [-h] [-p {http,https,socks4,socks5}] [-o OUTPUT]
                    [-i INPUT] [-t TIMEOUT] [-j] [--list-sources] [-q]

Options:
  -p, --proto     Proxy protocol: http, https, socks4, socks5 (default: http)
  -o, --output    Output file (default: output/<proto>_live.txt)
  -i, --input     Input file of proxies to validate (skips scraping)
  -t, --timeout   Timeout per check in seconds (default: 10)
  -j, --json      Also save detailed JSON results
  --list-sources  Show all scraping sources and exit
  -q, --quiet     Minimal output
```

## How Validation Works

Each proxy must pass **every** check to be included:

| Protocol | Validation Method |
|----------|-------------------|
| HTTP     | Request through proxy to httpbin.org/ip, icanhazip.com, api.ipify.org |
| HTTPS    | Same as HTTP + an HTTPS endpoint (https://httpbin.org/ip) |
| SOCKS4   | SOCKS4 CONNECT handshake to 3 different destinations |
| SOCKS5   | SOCKS5 CONNECT handshake to 3 different destinations |

A proxy that fails **any single check** is discarded. This ensures every proxy in the output is genuinely live and functional.

## Project Structure

```
proxy-scraper/
+-- main.py           # CLI entry point
+-- scraper.py        # Async proxy scraping from 30+ sources
+-- checker.py        # Strict multi-endpoint validation
+-- requirements.txt  # httpx, beautifulsoup4, rich
+-- output/           # Generated live proxy files
```

## Requirements

- Python 3.10+
- httpx
- beautifulsoup4
- rich

## License

MIT
