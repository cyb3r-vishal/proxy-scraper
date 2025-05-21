## How to Use the Auto Proxy Feature

The Auto Proxy feature in ProxyMaster is designed to provide a continuous supply of fresh, validated proxies with minimal effort.

### Quick Start

1. Open PowerShell and navigate to the ProxyMaster directory
2. Run the auto proxy with default settings:

```powershell
.\run-proxy.ps1 auto
```

This will start the auto proxy service with default settings:
- Scraping both HTTP and HTTPS proxies
- Running every 60 minutes
- Keeping up to 200 proxies of each type
- Testing against icanhazip.com and api.ipify.org
- Timeout of 5 seconds for validation

### Configuration Options

You can configure the auto proxy service using command-line parameters:

#### Change Proxy Types

```powershell
# Only HTTP proxies
.\run-proxy.ps1 auto -t http

# HTTP, SOCKS4, and SOCKS5 proxies
.\run-proxy.ps1 auto -t http,socks4,socks5

# All supported proxy types
.\run-proxy.ps1 auto -t http,https,socks4,socks5
```

#### Change Refresh Interval

```powershell
# Run every 15 minutes
.\run-proxy.ps1 auto -i 15

# Run every 2 hours
.\run-proxy.ps1 auto -i 120

# Run every day
.\run-proxy.ps1 auto -i 1440
```

#### Change Test Sites

```powershell
# Use multiple test sites
.\run-proxy.ps1 auto -s icanhazip.com,api.ipify.org,ifconfig.me

# Use a single test site for faster validation
.\run-proxy.ps1 auto -s icanhazip.com
```

#### Other Options

```powershell
# Increase timeout for more reliable validation
.\run-proxy.ps1 auto --timeout 10

# Keep more proxies (default is 200)
.\run-proxy.ps1 auto -m 500

# Don't run immediately on startup
.\run-proxy.ps1 auto --no-immediate
```

### Using the Generated Proxy Lists

The auto proxy service maintains several files:

1. **Live Proxy Files**:
   - `output/http_live.txt`
   - `output/https_live.txt`
   - `output/socks4_live.txt`
   - `output/socks5_live.txt`

   These files contain the current working proxies and are updated on each run.

2. **Historical Proxy Files**:
   - `output/{type}_proxies_{timestamp}.txt`: Raw scraped proxies
   - `output/{type}_valid_{timestamp}.txt`: Validated proxies 

To use the proxies with other tools, simply point them to the appropriate live file:

```powershell
# Use live HTTP proxies with the rotator
.\run-proxy.ps1 rotate -i output/http_live.txt

# Add geolocation data to live SOCKS5 proxies
.\run-proxy.ps1 geo -i output/socks5_live.txt
```

### Running in Background

To run the auto proxy service in the background, you can use:

```powershell
# Start the included batch file
.\start-auto-proxy.bat
```

Or run in a background PowerShell job:

```powershell
Start-Job -ScriptBlock { 
    cd "C:\Users\Vishal\Desktop\Python Projects\proxy-scraper" 
    .\run-proxy.ps1 auto 
}
```

### Checking Status

The auto proxy service will display its status on startup and after each run.

To check the status manually, you can:
1. Look at the timestamp on the live proxy files
2. Check the auto_proxy.log file
3. Check the number of proxies in the live files

```powershell
# Count proxies in a live file
(Get-Content output/http_live.txt).Count
```
