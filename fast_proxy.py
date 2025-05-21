#!/usr/bin/env python3
"""
Fast Proxy - Optimized proxy scraper and validator for maximum speed
"""

import asyncio
import os
import sys
import time
from datetime import datetime
import argparse

# Set up proper asyncio policy for Windows
if sys.platform == 'win32' and hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Import modules with fast fail if not available
try:
    # Local modules
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from proxyScraper import scrape
    
    # External modules
    import httpx
    from rich.console import Console
    from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "rich"])
    
    # Try again after installing
    import httpx
    from rich.console import Console
    from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

# Initialize console
console = Console()

# Optimized settings
MAX_CONCURRENT = 200
CONNECT_TIMEOUT = 3
READ_TIMEOUT = 5
TEST_URLS = ["http://httpbin.org/ip", "http://icanhazip.com"]

async def fast_validate(proxy, proxy_type):
    """Ultra-fast proxy validation"""
    start = time.time()
    try:
        # Setup optimized client with minimal timeout
        timeout = httpx.Timeout(total=5.0, connect=2.0)
        async with httpx.AsyncClient(
            proxies={
                "http://": f"{proxy_type}://{proxy}",
                "https://": f"{proxy_type}://{proxy}"
            },
            timeout=timeout,
            follow_redirects=True
        ) as client:
            # Use httpbin for ultra-fast response
            response = await client.get(TEST_URLS[0])
            
            if response.status_code == 200:
                return {
                    "proxy": proxy,
                    "working": True,
                    "response_time": time.time() - start,
                }
    except:
        pass
    
    return {
        "proxy": proxy,
        "working": False,
        "response_time": 999
    }

async def batch_validate(proxies, proxy_type, batch_size=100):
    """Validate proxies in high-speed batches"""
    results = []
    
    # Process in optimized batches
    for i in range(0, len(proxies), batch_size):
        batch = proxies[i:i+batch_size]
        tasks = [fast_validate(proxy, proxy_type) for proxy in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend([r for r in batch_results if r["working"]])
    
    return results

async def run_fast_proxy(proxy_type, output_file, max_runtime=3.0):
    """Run the fast proxy scraper and validator"""
    # Record start time
    start_time = time.time()
    console.print(f"[bold]Starting fast proxy scraper at {datetime.now().strftime('%H:%M:%S')}[/]")
    
    # Get a temporary file for scraped proxies
    temp_file = f"temp_{proxy_type}_{int(time.time())}.txt"
    
    # Step 1: Fast scrape (optimized)
    console.print("[bold green]1. Fast scraping proxies...[/]")
    scrape_start = time.time()
    count = await scrape(proxy_type, temp_file, verbose=True, fast_mode=True)
    console.print(f"[bold]Scraping completed in {time.time() - scrape_start:.2f} seconds[/]")
    
    # Check if we got any proxies and if we still have time
    if count == 0:
        console.print("[bold red]No proxies found![/]")
        return False
    
    # Load scraped proxies
    with open(temp_file, 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]
    
    # Step 2: Fast validation
    console.print(f"[bold green]2. Fast validating {len(proxies)} proxies...[/]")
    results = await batch_validate(proxies, proxy_type)
    
    # Step 3: Save results
    working_proxies = [r["proxy"] for r in results]
    
    if working_proxies:
        # Sort by speed
        results.sort(key=lambda x: x["response_time"])
        sorted_proxies = [r["proxy"] for r in results]
        
        # Save to output file
        with open(output_file, "w") as f:
            f.write("\n".join(sorted_proxies))
        
        # Calculate runtime
        runtime = time.time() - start_time
        
        # Show stats
        console.print(f"[bold green]Found {len(working_proxies)} working proxies in {runtime:.2f} seconds![/]")
        console.print(f"[bold green]Results saved to {output_file}[/]")
        
        # Show top 5 fastest
        if len(results) >= 5:
            console.print("[bold cyan]Top 5 fastest proxies:[/]")
            for i, proxy in enumerate(results[:5]):
                console.print(f"  {i+1}. {proxy['proxy']} - {proxy['response_time']:.3f}s")
    else:
        console.print("[bold red]No working proxies found![/]")
    
    # Clean up temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    # Return true if we found any working proxies
    return len(working_proxies) > 0

async def main():
    """Main function"""
    # Clear console
    console.clear()
    
    # Print banner
    console.print("[bold cyan]╔════════════════════════════════════════╗[/]")
    console.print("[bold cyan]║       FAST PROXY SCRAPER v1.0.0        ║[/]")
    console.print("[bold cyan]║    Optimized for maximum performance   ║[/]")
    console.print("[bold cyan]╚════════════════════════════════════════╝[/]")
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Fast Proxy - Optimized proxy scraper")
    parser.add_argument("-t", "--type", help="Proxy type (http, https, socks4, socks5)", default="http")
    parser.add_argument("-o", "--output", help="Output file", default="fast_proxies.txt")
    parser.add_argument("-m", "--max-time", help="Maximum runtime in seconds", type=float, default=3.0)
    
    args = parser.parse_args()
    
    # Run the fast proxy scraper
    await run_fast_proxy(args.type, args.output, args.max_time)

if __name__ == "__main__":
    # Run with proper asyncio handling
    if sys.version_info >= (3, 7):
        asyncio.run(main())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.close()
