# ProxyMaster 2.0 - Advanced Proxy Tools Suite

A comprehensive suite of tools for scraping, validating, and managing proxy lists with advanced features like geolocation data, automatic monitoring, proxy rotation, and ultra-fast scraping.

Created by **cyb3r_vishal** (community DevKitX)

![ProxyMaster Banner](https://img.shields.io/badge/ProxyMaster-2.0.0-blue)
![Python Version](https://img.shields.io/badge/Python-3.7%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Key Features

### Core Features
- **Multi-Source Scraping**: Collects proxies from 20+ different sources
- **Advanced Validation**: Tests proxies against multiple sites for better reliability
- **Proxy Analytics**: Track proxy performance metrics over time
- **Geolocation Data**: Adds country, city, ISP, and anonymity level information to proxies
- **Cross-Platform Support**: Windows (PowerShell) and Unix (Bash) systems

### ⚡ Performance Features
- **Ultra-Fast Mode**: Complete proxy scraping in ~3 seconds
- **High-Performance Scraping**: Optimized async code for maximum throughput
- **Smart Caching**: Memory and disk caching for repeated validations
- **Batch Processing**: Processes proxies in optimized batches
- **Multi-threaded Operations**: Utilize all CPU cores efficiently

### 🛠️ Advanced Tools
- **Auto Proxy**: Fully automated scraping and validation service that runs on a schedule
- **Proxy Monitoring**: Periodically re-checks proxies to maintain fresh lists
- **Proxy Rotation Server**: Intelligent rotation with automatic failover
- **Visual Analytics**: Generate performance charts and reports
- **Benchmarking**: Compare proxy speed and reliability

## 📋 Quick Start

### Windows (PowerShell)
```powershell
# Get and validate HTTP proxies
.\run-proxy.ps1 http

# Get and validate SOCKS5 proxies
.\run-proxy.ps1 socks5

# Ultra-fast mode (completes in ~3 seconds)
.\fast-proxy.ps1 -ProxyType http -Ultra

# Start the auto proxy service (runs in background)
.\run-proxy.ps1 auto -t http,https -i 30

# Generate proxy analytics report
.\run-proxy.ps1 analytics report -t summary
```

### Linux/MacOS (Bash)
```bash
# Get and validate HTTP proxies
./run-proxy.sh http

# Get and validate SOCKS5 proxies
./run-proxy.sh socks5

# Start the auto proxy service
./run-proxy.sh auto -t http,https -i 30
```

### Python Direct Usage
```bash
# Ultra-fast proxy scraping
python fast_proxy.py --type http

# Standard scraping and validation
python proxymaster.py --type http --output proxies.txt --validate

# Generate analytics report
python proxy_analytics.py report --type summary
```

## 📊 Analytics Feature

ProxyMaster includes comprehensive analytics capabilities to track and analyze proxy performance over time:

```powershell
# Generate performance summary
.\run-proxy.ps1 analytics report -t summary

# Generate trend report for last 14 days
.\run-proxy.ps1 analytics report -t trend -d 14

# List top performing proxies
.\run-proxy.ps1 analytics report -t top_proxies -p http
```

## 🔄 Proxy Rotation

Start the intelligent proxy rotation server:

```powershell
# Start the rotation server on port 8080
.\run-proxy.ps1 rotate -i proxies.txt -p 8080

# For maximum performance
.\run-proxy.ps1 rotate -i fast_proxies.txt -p 8080 -r 20
```

## 📱 GUI Interface

ProxyMaster includes a graphical user interface:

```bash
# Start the GUI
python proxymaster_gui.py
```

The GUI includes tabs for:
- Scraping & Validation
- Proxy Monitoring
- Geolocation
- Proxy Rotation
- Analytics

## 🧰 Installation

```bash
# Clone or download the repository
git clone https://github.com/yourusername/proxy-scraper.git
cd proxy-scraper

# Install dependencies
python install.py
# or
pip install -r requirements.txt
```

## 🌐 Advanced Usage

### Proxy Benchmarking
```bash
python proxy_benchmark.py --input proxies.txt --output benchmark_results.txt --sort
```

### Geo-Tagging
```bash
python proxy_geo.py --input proxies.txt --output geo_proxies.json
```

### Custom Integration

```python
from proxymaster import scrape_proxies, validate_proxies

# Scrape proxies
proxies = scrape_proxies("http")

# Validate proxies
valid_proxies = validate_proxies(proxies, timeout=10)

for proxy in valid_proxies:
    print(f"{proxy.address} - Success Rate: {proxy.success_rate}%")
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📧 Contact

Created by **cyb3r_vishal** (community DevKitX) - feel free to connect!

---

⭐ Star this repository if you found it useful!
.\run-proxy.ps1 help
```

### Unix (Bash)
```bash
# Make the script executable
chmod +x run-proxy.sh

# Get and validate HTTP proxies
./run-proxy.sh http

# Get and validate SOCKS5 proxies
./run-proxy.sh socks5

# Show help with all available commands
./run-proxy.sh help
```

## Advanced Usage

### Proxy Master (Main Tool)
```bash
# Scrape and validate HTTP proxies with custom timeout and success rate
python proxymaster.py -p http -t 15 -m 0.5

# Validate existing proxy list against specific test sites
python proxymaster.py -p https -i my_proxies.txt -s icanhazip.com,ifconfig.me
```

### Proxy Monitor (Automatic Re-checking)
```bash
# Monitor HTTP proxies, checking every 30 minutes
python proxy_monitor.py -p http -n 30

# Check SOCKS5 proxies once with extended timeout
python proxy_monitor.py -p socks5 --once -t 20
```

### Proxy Geo (Geolocation Data)
```bash
# Add geolocation data to proxy list
python proxy_geo.py -i output/http_live.txt

# Specify custom output file
python proxy_geo.py -i output/socks5_live.txt -o output/socks5_geo.json
```

### Proxy Rotator (Rotating Proxy Server)
```bash
# Start a rotating proxy server on default port (8080)
python proxy_rotator.py -i output/http_geo.txt

# Configure rotation frequency and port
python proxy_rotator.py -i output/socks5_live.txt -p 9000 -r 10

# Skip proxy testing before starting server
python proxy_rotator.py -i output/http_live.txt --no-test
```

## GUI Mode

ProxyMaster now includes a full graphical user interface that provides access to all features in a user-friendly way. The GUI includes:

- **Scraper & Validator Tab**: Scrape, validate, or both in one step
- **Proxy Monitor Tab**: Schedule automatic checking of proxies
- **Geolocation Tab**: Add and visualize geolocation data for proxies
- **Proxy Rotator Tab**: Run an intelligent rotating proxy server

### Starting the GUI

```bash
# Launch the GUI
python gui/proxymaster_gui.py
```

### Features by Tab

#### Scraper & Validator
- Select proxy type (HTTP, HTTPS, SOCKS4, SOCKS5)
- Adjust timeout settings via slider
- Set minimum success rate requirements
- Specify test sites
- Load existing proxy lists
- Run scraping, validation, or both

#### Proxy Monitor
- Select proxy file to monitor
- Set check interval in minutes
- Run once or continuously monitor
- View checking history and statistics
- Track success rates over time

#### Geolocation
- Add geolocation data to any proxy list
- View country, city, ISP, and anonymity information
- See statistics about country and anonymity distribution
- Sort and filter proxies by location

#### Proxy Rotator
- Start a rotating proxy server from the GUI
- Configure port and rotation settings
- Test connection directly from the interface
- Monitor proxy performance in real-time
- View statistics on success/failure rates

### Screenshot
![ProxyMaster GUI](https://raw.githubusercontent.com/username/proxymaster/main/gui/screenshot.png)

## Telegram Integration

ProxyMaster now supports sending valid proxies directly to a Telegram chat. This feature allows you to:
- Send validated proxies in batches to a Telegram bot
- Receive live updates as proxies are validated
- Easily share working proxies with team members

### Setting Up Telegram Integration

1. **Create a Telegram Bot**:
   - Talk to [@BotFather](https://t.me/botfather) on Telegram
   - Use the `/newbot` command to create a new bot
   - Save the API token provided by BotFather

2. **Get Your Chat ID**:
   - Send a message to your bot
   - Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find the `chat_id` in the JSON response

3. **Use with ProxyMaster CLI**:
   ```powershell
   # Send valid proxies to Telegram in batches of 100
   python proxymaster.py -p http --telegram-token "YOUR_BOT_TOKEN" --telegram-chat "YOUR_CHAT_ID"
   
   # Change the batch size
   python proxymaster.py -p socks5 --telegram-token "YOUR_BOT_TOKEN" --telegram-chat "YOUR_CHAT_ID" --telegram-batch 50
   ```

### Example with run-proxy.ps1

```powershell
# Using PowerShell wrapper with Telegram integration
.\run-proxy.ps1 http -telegram "YOUR_BOT_TOKEN" "YOUR_CHAT_ID"
```

The script will notify you when batches of proxies are sent to Telegram. This is particularly useful for long validation sessions where you want to start using the first validated proxies immediately.

## Integration

The GUI and CLI components are fully integrated, sharing the same core functionality. Files created by either interface can be used interchangeably.

## Command Line Reference

### ProxyMaster
```
python proxymaster.py [options]

Options:
  -p, --proxy           Proxy type (http, https, socks4, socks5) [default: http]
  -t, --timeout         Timeout in seconds for validation [default: 10]
  -s, --sites           Comma-separated test sites [default: icanhazip.com,api.ipify.org,ifconfig.me]
  -m, --min-success     Minimum success rate (0.0 to 1.0) [default: 0.25]
  -i, --input           Input file with proxies (skips scraping if provided)
  -v, --verbose         Enable verbose output
  --telegram-token      Telegram bot token for sending proxy lists
  --telegram-chat       Telegram chat ID to send proxy lists to
  --telegram-batch      Send proxies to Telegram in batches of this size [default: 100]
```

**Stopping validation**: You can stop the validation process at any time by:
- Pressing Ctrl+C in the terminal
- Typing 'stop' in the terminal while validation is running

### Proxy Monitor
```
python proxy_monitor.py [options]

Options:
  -p, --proxy       Proxy type to monitor [default: http]
  -i, --input       Input file with proxies to monitor
  -t, --timeout     Timeout in seconds for validation [default: 10]
  -n, --interval    Check interval in minutes [default: 60]
  --once            Run once and exit (don't run as a service)
```

### Proxy Geo
```
python proxy_geo.py [options]

Options:
  -i, --input       Input file with proxies (required)
  -o, --output      Output JSON file with geolocation data
```

### Proxy Rotator
```
python proxy_rotator.py [options]

Options:
  -p, --port        Port to run the proxy server on [default: 8080]
  -i, --input       Input file with proxies (required)
  -r, --rotation    Number of requests before rotating proxy [default: 20]
  -t, --timeout     Timeout in seconds for proxy requests [default: 10]
  --no-test         Skip testing proxies before starting server
```

## Output Files

The tools generate the following output files in the `output` directory:

- `{type}_proxies_{timestamp}.txt` - All scraped proxies
- `{type}_valid_{timestamp}.txt` - Validated proxies
- `{type}_valid_{timestamp}.json` - Detailed validation data
- `{type}_live.txt` - Latest valid proxies
- `{type}_geo.json` - Proxies with geolocation data
- `{type}_geo.txt` - Text version of geolocation data
- `{type}_history.json` - History of proxy checking runs

## Tips for Best Results

1. Use `icanhazip.com` as your primary test site (most reliable)
2. Set a timeout of 10-15 seconds for better accuracy
3. Test against multiple sites to ensure proxy reliability
4. For faster results with lower quality, reduce the minimum success rate (`-m 0.1`)
5. For higher quality proxies, increase the minimum success rate (`-m 0.5`)
6. Use the proxy rotation server for applications that need to cycle through proxies
7. Regularly monitor your proxies to maintain a fresh list of working IPs

## Proxy Sources

ProxyMaster scrapes proxies from various sources including:

- sslproxies.org (HTTP, HTTPS)
- free-proxy-list.net (HTTP, HTTPS)
- us-proxy.org (HTTP, HTTPS)
- socks-proxy.net (Socks4, Socks5)
- proxyscrape.com (HTTP, Socks4, Socks5)
- proxy-list.download (HTTP, HTTPS, Socks4, Socks5)
- geonode.com (HTTP, HTTPS, Socks4, Socks5)
- GitHub repositories with proxy lists

## Example Workflow

Here's a complete workflow example:

1. **Scrape and validate proxies**:
   ```powershell
   .\run-proxy.ps1 http
   ```

2. **Add geolocation data**:
   ```powershell
   .\run-proxy.ps1 geo -i output/http_live.txt
   ```

3. **Start monitoring service**:
   ```powershell
   .\run-proxy.ps1 monitor -p http -n 30
   ```

4. **Use the rotating proxy server**:
   ```powershell
   .\run-proxy.ps1 rotate -i output/http_geo.txt
   ```

Then configure your application to use `http://localhost:8080` as the proxy.

## License

MIT License

Copyright (c) 2025 cyb3r_vishal (community DevKitX)
