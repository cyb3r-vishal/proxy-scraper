"""
Proxy Scraper - Fetches free proxies from multiple reliable sources.
Supports HTTP, HTTPS, SOCKS4, SOCKS5.
"""

import asyncio
import re

import httpx
from bs4 import BeautifulSoup

SOURCES = {
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
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

IP_PORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}:\d{1,5})\b")

TABLE_SITES = frozenset([
    "free-proxy-list.net",
    "us-proxy.org",
    "sslproxies.org",
    "socks-proxy.net",
])


def _is_table_site(url: str) -> bool:
    return any(site in url for site in TABLE_SITES)


def _parse_table(html: str, url: str, proxy_type: str) -> set[str]:
    """Parse proxy table HTML pages."""
    proxies: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")

    # Try multiple selectors — these sites change structure often
    table = soup.find("table", {"id": "proxylisttable"})
    if table is None:
        table = soup.find("table", {"class": "table"})
    if table is None:
        # Fallback: extract with regex
        return set(IP_PORT_RE.findall(html))

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        ip = cells[0].get_text(strip=True)
        port = cells[1].get_text(strip=True)
        if not ip or not port:
            continue

        # Type filtering for socks-proxy.net
        if "socks-proxy.net" in url and len(cells) > 4:
            row_type = cells[4].get_text(strip=True).lower()
            if proxy_type not in row_type:
                continue

        # HTTPS filtering for SSL proxy sites
        if proxy_type == "https" and len(cells) > 6:
            https_flag = cells[6].get_text(strip=True).lower()
            if https_flag != "yes":
                continue

        proxies.add(f"{ip}:{port}")

    return proxies


def _parse_plain(text: str) -> set[str]:
    """Extract IP:PORT from plain text."""
    return set(IP_PORT_RE.findall(text))


async def _fetch_source(
    client: httpx.AsyncClient, url: str, proxy_type: str
) -> set[str]:
    """Fetch and parse proxies from a single source."""
    for attempt in range(2):
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return set()

            if _is_table_site(url):
                return _parse_table(resp.text, url, proxy_type)
            return _parse_plain(resp.text)

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError):
            if attempt == 1:
                return set()
            await asyncio.sleep(0.5)

    return set()


def _validate_ip_port(proxy: str) -> bool:
    """Quick format validation: valid IP octets and port range."""
    parts = proxy.split(":")
    if len(parts) != 2:
        return False
    ip_parts = parts[0].split(".")
    if len(ip_parts) != 4:
        return False
    try:
        for octet in ip_parts:
            if not 0 <= int(octet) <= 255:
                return False
        port = int(parts[1])
        return 1 <= port <= 65535
    except ValueError:
        return False


async def scrape(proxy_type: str) -> list[str]:
    """
    Scrape proxies of the given type from all sources.

    Args:
        proxy_type: One of 'http', 'https', 'socks4', 'socks5'.

    Returns:
        Deduplicated list of proxy strings (ip:port).
    """
    proxy_type = proxy_type.lower()
    if proxy_type not in SOURCES:
        raise ValueError(
            f"Unsupported proxy type '{proxy_type}'. "
            f"Choose from: {', '.join(SOURCES.keys())}"
        )

    sources = SOURCES[proxy_type]

    timeout = httpx.Timeout(10.0, connect=5.0, read=8.0)
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=10)

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers=HEADERS,
        follow_redirects=True,
    ) as client:
        tasks = [_fetch_source(client, url, proxy_type) for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_proxies: set[str] = set()
    for result in results:
        if isinstance(result, set):
            all_proxies.update(result)

    # Filter out malformed entries
    valid = [p for p in all_proxies if _validate_ip_port(p)]
    valid.sort()
    return valid
