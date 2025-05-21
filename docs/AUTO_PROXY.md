# Auto Proxy Feature

The Auto Proxy feature is a powerful automated tool that continuously scrapes and validates proxies in the background, maintaining a fresh pool of working proxies at all times.

## Overview

The Auto Proxy tool runs as a background service that:
1. Scrapes proxies from multiple sources on a schedule
2. Validates the scraped proxies for functionality 
3. Maintains a database of working proxies
4. Automatically refreshes the proxy pool at configurable intervals

## Usage

### Basic Usage

```powershell
# Start auto proxy with default settings (HTTP and HTTPS proxies every 60 minutes)
.\run-proxy.ps1 auto

# Start auto proxy with specific proxy types and interval
.\run-proxy.ps1 auto -t http,socks4,socks5 -i 30

# Start auto proxy with more validation test sites
.\run-proxy.ps1 auto -s icanhazip.com,api.ipify.org,ifconfig.me

# Run auto proxy with a larger pool size
.\run-proxy.ps1 auto -m 500
```

### Advanced Options

```powershell
# Start auto proxy without immediate first run
.\run-proxy.ps1 auto --no-immediate

# Run with increased timeout for more thorough validation
.\run-proxy.ps1 auto --timeout 10

# Run with detailed verbose output
.\run-proxy.ps1 auto -v
```

## Command-line Parameters

| Parameter | Description | Default |
| --- | --- | --- |
| `-t, --types` | Comma-separated list of proxy types to scrape | http,https |
| `-i, --interval` | Refresh interval in minutes | 60 |
| `-m, --max-proxies` | Maximum number of proxies to keep per type | 200 |
| `--timeout` | Timeout in seconds for proxy validation | 5 |
| `-s, --sites` | Comma-separated list of sites to validate against | icanhazip.com,api.ipify.org |
| `--no-immediate` | Don't run proxy scraping immediately on start | false |
| `-v, --verbose` | Enable verbose output | false |

## How It Works

1. **Scheduling**: The tool uses the `schedule` library to run scraping jobs at the specified interval
2. **Scraping**: On each run, it collects proxies from multiple sources for each selected proxy type
3. **Validation**: It asynchronously validates each proxy against the specified test sites
4. **Caching**: Successful validation results are cached to speed up future validation
5. **Storage**: Valid proxies are saved to both timestamped and live files in the output directory

## File Output

For each proxy type, the following files are created or updated:
- `output/{type}_proxies_{timestamp}.txt`: Raw scraped proxies from a specific run
- `output/{type}_valid_{timestamp}.txt`: Validated proxies from a specific run
- `output/{type}_live.txt`: Current working proxies of this type (updated on each run)

## Architecture

The Auto Proxy feature uses:
- Asynchronous I/O with `asyncio` and `aiohttp` for maximum performance
- Connection pooling to optimize network resources
- Intelligent caching of validation results
- Concurrent validation with configurable batch sizes
- Background thread for scheduling that doesn't block the main application

## Integration with Other Tools

The Auto Proxy feature integrates well with other ProxyMaster tools:

- **Proxy Monitor**: Use Auto Proxy to fill the proxy pool, then monitor with Proxy Monitor
- **Proxy Rotator**: Point the rotator to the `_live.txt` files for a self-refreshing proxy rotation server
- **Geo Data**: Run the geo tool on the live files to add geolocation data
