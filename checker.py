"""
Proxy Checker - Validates proxies to ensure they are 100% live.
Each proxy is tested against multiple endpoints and must pass ALL checks.
Supports HTTP, HTTPS, SOCKS4, SOCKS5.
"""

import asyncio
import re
import socket
import struct
import time
from dataclasses import dataclass, field

import httpx

# Validation endpoints — proxy must respond correctly on ALL of these
VALIDATION_URLS = [
    "http://icanhazip.com",
    "http://api.ipify.org",
    "http://ip.me",
]

# HTTPS endpoint for HTTPS proxy verification
HTTPS_VALIDATION_URL = "https://api.ipify.org"

IP_PATTERN = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")

# Concurrency limits
MAX_CONCURRENT = 100
TIMEOUT_SECONDS = 6
BATCH_SIZE = 200
PORT_CHECK_TIMEOUT = 2.0  # Fast pre-filter


@dataclass
class ProxyResult:
    """Result of validating a single proxy."""
    proxy: str
    proto: str
    alive: bool = False
    response_time: float = 0.0
    ip_returned: str = ""
    checks_passed: int = 0
    checks_total: int = 0
    error: str = ""


async def _port_open(host: str, port: int, timeout: float = PORT_CHECK_TIMEOUT) -> bool:
    """Quick TCP port check — eliminates dead proxies in <2s."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
#  SOCKS helpers (pure-Python, no external SOCKS lib needed for checking)
# ---------------------------------------------------------------------------

async def _socks4_connect(
    host: str, port: int, dest_host: str, dest_port: int, timeout: float
) -> bool:
    """Attempt a SOCKS4 CONNECT handshake."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except (asyncio.TimeoutError, OSError):
        return False

    try:
        # SOCKS4 CONNECT request
        dest_ip = socket.inet_aton(socket.gethostbyname(dest_host))
        req = struct.pack(">BBH", 0x04, 0x01, dest_port) + dest_ip + b"\x00"
        writer.write(req)
        await writer.drain()

        resp = await asyncio.wait_for(reader.read(8), timeout=timeout)
        # Byte 1 == 0x5A means request granted
        return len(resp) >= 2 and resp[1] == 0x5A
    except (asyncio.TimeoutError, OSError):
        return False
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _socks5_connect(
    host: str, port: int, dest_host: str, dest_port: int, timeout: float
) -> bool:
    """Attempt a SOCKS5 CONNECT handshake."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except (asyncio.TimeoutError, OSError):
        return False

    try:
        # Greeting: version 5, 1 auth method (no auth)
        writer.write(b"\x05\x01\x00")
        await writer.drain()

        resp = await asyncio.wait_for(reader.read(2), timeout=timeout)
        if len(resp) < 2 or resp[0] != 0x05 or resp[1] != 0x00:
            return False

        # CONNECT request
        dest_ip = socket.inet_aton(socket.gethostbyname(dest_host))
        req = (
            struct.pack(">BBB", 0x05, 0x01, 0x00)
            + b"\x01"  # IPv4
            + dest_ip
            + struct.pack(">H", dest_port)
        )
        writer.write(req)
        await writer.drain()

        resp = await asyncio.wait_for(reader.read(10), timeout=timeout)
        return len(resp) >= 2 and resp[1] == 0x00
    except (asyncio.TimeoutError, OSError):
        return False
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


# ---------------------------------------------------------------------------
#  HTTP / HTTPS check via httpx
# ---------------------------------------------------------------------------

async def _check_http_proxy(
    proxy_str: str, url: str, timeout: float
) -> tuple[bool, float, str]:
    """
    Test an HTTP/HTTPS proxy by making a request through it.
    Returns (success, response_time, ip_returned).
    """
    proxy_url = f"http://{proxy_str}"
    t = httpx.Timeout(timeout, connect=3.0, read=timeout)

    try:
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=t,
            follow_redirects=True,
        ) as client:
            start = time.monotonic()
            resp = await client.get(url)
            elapsed = time.monotonic() - start

            if resp.status_code != 200:
                return False, elapsed, ""

            body = resp.text.strip()
            match = IP_PATTERN.search(body)
            ip = match.group(0) if match else ""
            return bool(ip), elapsed, ip

    except Exception:
        return False, 0.0, ""


# ---------------------------------------------------------------------------
#  Single proxy validation (all types)
# ---------------------------------------------------------------------------

async def check_proxy(proxy_str: str, proto: str) -> ProxyResult:
    """
    Validate a single proxy. Must pass ALL validation endpoints to be
    considered live.
    """
    result = ProxyResult(proxy=proxy_str, proto=proto)
    parts = proxy_str.split(":")
    if len(parts) != 2:
        result.error = "invalid format"
        return result

    host, port_str = parts
    try:
        port = int(port_str)
    except ValueError:
        result.error = "invalid port"
        return result

    # Quick port check — skip proxies with closed ports immediately
    if not await _port_open(host, port):
        result.error = "port closed"
        return result

    total_time = 0.0
    passed = 0
    first_ip = ""

    try:
        if proto in ("http", "https"):
            # Test against all validation URLs
            urls = VALIDATION_URLS[:]
            if proto == "https":
                urls.append(HTTPS_VALIDATION_URL)

            result.checks_total = len(urls)

            for url in urls:
                ok, elapsed, ip = await _check_http_proxy(
                    proxy_str, url, TIMEOUT_SECONDS
                )
                if ok:
                    passed += 1
                    total_time += elapsed
                    if not first_ip and ip:
                        first_ip = ip
                else:
                    # Fail fast: if ANY check fails, proxy is not 100% live
                    break

        elif proto in ("socks4", "socks5"):
            # For SOCKS we do a handshake test to multiple destinations
            test_targets = [
                ("icanhazip.com", 80),
                ("api.ipify.org", 80),
                ("ip.me", 80),
            ]
            result.checks_total = len(test_targets)

            connect_fn = _socks4_connect if proto == "socks4" else _socks5_connect

            for dest_host, dest_port in test_targets:
                start = time.monotonic()
                ok = await connect_fn(host, port, dest_host, dest_port, TIMEOUT_SECONDS)
                elapsed = time.monotonic() - start
                if ok:
                    passed += 1
                    total_time += elapsed
                else:
                    break
    except Exception:
        pass

    result.checks_passed = passed
    result.alive = passed == result.checks_total and passed > 0
    result.response_time = round(total_time / max(passed, 1), 3)
    result.ip_returned = first_ip
    return result


# ---------------------------------------------------------------------------
#  Batch validation with concurrency control
# ---------------------------------------------------------------------------

async def check_all(
    proxies: list[str],
    proto: str,
    on_progress=None,
    target: int = 0,
) -> list[ProxyResult]:
    """
    Validate all proxies in batches with bounded concurrency.

    Args:
        proxies: List of 'ip:port' strings.
        proto: Protocol type.
        on_progress: Optional callback(checked: int, total: int, result: ProxyResult)
        target: Stop early once this many live proxies found (0 = check all).

    Returns:
        List of ProxyResult for proxies that passed ALL checks (100% live).
    """
    total = len(proxies)
    checked = 0
    live: list[ProxyResult] = []

    # Process in batches to avoid overwhelming the OS with connections
    for batch_start in range(0, total, BATCH_SIZE):
        batch = proxies[batch_start : batch_start + BATCH_SIZE]
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def _task(proxy_str: str):
            async with sem:
                try:
                    return await asyncio.wait_for(
                        check_proxy(proxy_str, proto),
                        timeout=TIMEOUT_SECONDS * 4,
                    )
                except asyncio.TimeoutError:
                    return ProxyResult(proxy=proxy_str, proto=proto, error="timeout")

        results = await asyncio.gather(
            *[_task(p) for p in batch], return_exceptions=True
        )

        for r in results:
            checked += 1
            if isinstance(r, ProxyResult):
                if r.alive:
                    live.append(r)
                if on_progress:
                    on_progress(checked, total, r)
            else:
                dummy = ProxyResult(proxy="?", proto=proto)
                if on_progress:
                    on_progress(checked, total, dummy)

        # Early stop if we've reached the target
        if target > 0 and len(live) >= target:
            break

    # Sort by response time (fastest first)
    live.sort(key=lambda r: r.response_time)
    return live
