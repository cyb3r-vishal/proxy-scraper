#!/usr/bin/env python3
"""
Proxy Scraper Module - Scrapes free proxies from various sources
"""

import asyncio
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

# Check for required packages and install if missing
try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    print("Installing required packages for proxy scraping...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "beautifulsoup4"])
    import httpx
    from bs4 import BeautifulSoup

# Optimized timeouts and connection settings
CONNECT_TIMEOUT = 3  # Ultra-fast initial connection timeout
READ_TIMEOUT = 5    # Faster read timeout
MAX_CONNECTIONS = 200  # Increased maximum concurrent connections
RETRY_COUNT = 2     # Reduced retries for faster execution

# List of proxy sources
PROXY_SOURCES = {
    "http": [
        "https://www.sslproxies.org/",
        "https://free-proxy-list.net/",
        "https://us-proxy.org/",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    ],
    "https": [
        "https://www.sslproxies.org/",
        "https://free-proxy-list.net/",
        "https://us-proxy.org/",
        "https://www.proxy-list.download/api/v1/get?type=https",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&ssl=true",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt",
    ],
    "socks4": [
        "https://www.socks-proxy.net/",
        "https://www.proxy-list.download/api/v1/get?type=socks4",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    ],
    "socks5": [
        "https://www.socks-proxy.net/",
        "https://www.proxy-list.download/api/v1/get?type=socks5",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    ],
}

# Headers for making HTTP requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


async def scrape_from_url(url, proxy_type, verbose=False):
    """Scrape proxies from a URL with optimized error handling"""
    proxies = set()
    if verbose:
        print(f"Scraping from: {url}")
    
    # Try with retries for reliability
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            # Faster timeout settings
            timeout = httpx.Timeout(6.0, connect=CONNECT_TIMEOUT, read=READ_TIMEOUT)
            async with httpx.AsyncClient(
                timeout=timeout, 
                headers=HEADERS, 
                limits=httpx.Limits(max_connections=MAX_CONNECTIONS),
                follow_redirects=True  # Follow redirects automatically
            ) as client:
                response = await client.get(url)
                break  # Success, exit retry loop
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            if attempt < RETRY_COUNT and verbose:
                print(f"Timeout error on {url}, attempt {attempt}/{RETRY_COUNT}")
            if attempt == RETRY_COUNT:
                if verbose:
                    print(f"Failed to connect to {url} after {RETRY_COUNT} attempts: {str(e)}")
                return proxies
    
    try:
            
        if response.status_code != 200:
            if verbose:
                print(f"Failed to retrieve from {url}: Status {response.status_code}")
            return proxies
        
        # Different parsing based on URL
        if "free-proxy-list.net" in url or "us-proxy.org" in url or "sslproxies.org" in url or "socks-proxy.net" in url:            # Parse table-based sites
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", {"id": "proxylisttable"})
            
            if not table:
                return proxies
            
            # Get table rows
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) > 1:
                    ip = cells[0].text.strip()
                    port = cells[1].text.strip()
                    
                    # Check if proxy matches required type
                    if "socks-proxy.net" in url:
                        row_type = cells[4].text.strip().lower()
                        if proxy_type.lower() not in row_type:
                            continue
                    elif "sslproxies.org" in url or ("free-proxy-list.net" in url and proxy_type == "https"):
                        https_cell = cells[6].text.strip().lower()
                        if proxy_type == "https" and https_cell != "yes":
                            continue
                        if proxy_type == "http" and https_cell == "yes":
                            continue
                    
                    # Add proxy to set
                    proxy = f"{ip}:{port}"
                    proxies.add(proxy)
        else:
            # Plain text proxies
            content = response.text
            
            # Find all IP:PORT patterns
            pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b"
            found_proxies = re.findall(pattern, content)
            
            # Add to our set
            proxies.update(found_proxies)
    
    except Exception as e:
        if verbose:
            print(f"Error scraping from {url}: {str(e)}")
    
    return proxies


async def scrape(proxy_type, output_file, verbose=False, fast_mode=True):
    """Main function to scrape proxies of a specific type with fast mode option"""
    if proxy_type.lower() not in PROXY_SOURCES:
        raise ValueError(f"Unsupported proxy type: {proxy_type}. Use http, https, socks4, or socks5.")
    
    # Create output directory if needed (only if it doesn't exist)
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get sources for this proxy type
    sources = PROXY_SOURCES[proxy_type.lower()]
    
    # In fast mode, use only the most reliable and fastest sources
    if fast_mode:
        # These are the typically most reliable and fastest sources
        fast_sources = [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",  # Usually very reliable
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",        # Fast API service
            "https://www.proxy-list.download/api/v1/get?type=http"                     # Another fast API
        ]
        # Use the specified fast sources if they're in our source list, otherwise use the first 2
        sources = [src for src in fast_sources if src in sources]
        if not sources and len(PROXY_SOURCES[proxy_type.lower()]) > 0:
            sources = PROXY_SOURCES[proxy_type.lower()][:2]
    
    if verbose:
        print(f"Scraping {proxy_type} proxies from {len(sources)} sources...")
      # Scrape from all sources concurrently with optimized gathering
    results = await asyncio.gather(*[scrape_from_url(url, proxy_type, verbose) for url in sources])
    
    # Combine results directly to a set for faster deduplication
    all_proxies = set().union(*results)
    
    # Skip sorting for speed in fast mode
    unique_proxies = list(all_proxies)
    
    # Faster file writing (write all at once)
    with open(output_file, "w") as f:
        f.write('\n'.join(unique_proxies))
    
    if verbose:
        print(f"Scraped {len(unique_proxies)} unique {proxy_type} proxies and saved to {output_file}")
    
    return len(unique_proxies)


# For testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Proxy Scraper")
    parser.add_argument("-t", "--type", help="Proxy type (http, https, socks4, socks5)", default="http")
    parser.add_argument("-o", "--output", help="Output file", default="proxies.txt")
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument("-f", "--fast", help="Fast mode - use fewer sources for quicker results", action="store_true", default=True)
    
    args = parser.parse_args()
    
    # Use optimized event loop policy if available
    if sys.platform == 'win32' and hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    if sys.version_info >= (3, 7):
        asyncio.run(scrape(args.type, args.output, args.verbose, args.fast))
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scrape(args.type, args.output, args.verbose, args.fast))
        loop.close()
