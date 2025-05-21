"""
Optimized proxy validator module with concurrent validation and caching
"""

import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import socket
import socks
from urllib.parse import urlparse
import random
from proxy_cache import ProxyCache

# Initialize cache
proxy_cache = ProxyCache()

# Configuration
MAX_CONCURRENT_CHECKS = 200  # Doubled concurrent checks
CONNECT_TIMEOUT = 3  # Faster connection timeout
READ_TIMEOUT = 5  # Faster read timeout
VALIDATION_BATCH_SIZE = 100  # Larger batch size for better throughput

async def check_proxy(proxy: str, proxy_type: str, test_url: str, timeout: int) -> tuple:
    """Check a single proxy asynchronously"""
    # Fast cache lookup first - avoid any processing if possible
    cached = proxy_cache.get(proxy)
    if cached:
        return proxy, cached['valid'], cached.get('response_time', 0), None
        
    start_time = time.time()
    url = f"http://{test_url}"
    
    try:

        if proxy_type in ['socks4', 'socks5']:
            # SOCKS proxies need special handling
            host, port = proxy.split(':')
            if proxy_type == 'socks4':
                proxy_url = f'socks4://{proxy}'
                socks_type = socks.SOCKS4
            else:
                proxy_url = f'socks5://{proxy}'
                socks_type = socks.SOCKS5
        else:
            proxy_url = f'{proxy_type}://{proxy}'

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(
                    total=timeout,
                    connect=CONNECT_TIMEOUT,
                    sock_read=READ_TIMEOUT
                )
            ) as response:
                if response.status == 200:
                    response_time = time.time() - start_time
                    # Cache successful result
                    proxy_cache.set(proxy, {
                        'valid': True,
                        'response_time': response_time
                    })
                    return proxy, True, response_time, None
                else:
                    proxy_cache.set(proxy, {'valid': False})
                    return proxy, False, 0, f"Status: {response.status}"

    except Exception as e:
        proxy_cache.set(proxy, {'valid': False})
        return proxy, False, 0, str(e)

async def validate_proxy_batch(proxies: List[str], proxy_type: str, test_url: str, timeout: int) -> List[dict]:
    """Validate a batch of proxies concurrently with optimized gathering"""
    # Pre-allocate task list for better memory efficiency
    tasks = [check_proxy(proxy, proxy_type, test_url, timeout) for proxy in proxies]
    
    # Use return_exceptions=True for higher throughput (prevents one failure from blocking)
    # This is faster than creating tasks in a loop
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_proxies = []
    for result in results:
        if isinstance(result, tuple) and result[1]:  # If valid
            valid_proxies.append({
                'proxy': result[0],
                'response_time': result[2]
            })
    
    return valid_proxies

async def validate_all_proxies(proxies: List[str], proxy_type: str, test_url: str, timeout: int) -> List[dict]:
    """Validate all proxies in optimized batches"""
    all_valid_proxies = []
    
    # Process in batches
    for i in range(0, len(proxies), VALIDATION_BATCH_SIZE):
        batch = proxies[i:i + VALIDATION_BATCH_SIZE]
        valid_batch = await validate_proxy_batch(batch, proxy_type, test_url, timeout)
        all_valid_proxies.extend(valid_batch)
    
    # Sort by response time
    return sorted(all_valid_proxies, key=lambda x: x['response_time'])
