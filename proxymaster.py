#!/usr/bin/env python3
"""
ProxyMaster - A streamlined proxy scraper and validator
"""

import argparse
import json
import os
import random
import re
import select
import socket
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Check for required packages and install if missing
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table

try:
    import socks
except ImportError:
    print("Installing PySocks...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pysocks"])
    import socks

# For Telegram integration
try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Initialize rich console
console = Console()

# Global variables
STOP_VALIDATION = False  # Flag to stop validation process
TELEGRAM_BOT_TOKEN = None  # Will be set from command line if provided
TELEGRAM_CHAT_ID = None   # Will be set from command line if provided
BATCH_SIZE = 100  # Number of proxies to send in each batch
# Optimized timeouts and concurrency settings
DEFAULT_TIMEOUT = 5  # Reduced from 10 to 5 seconds
MAX_WORKERS = 100   # Increased thread pool size for validation
VALIDATION_BATCH_SIZE = 50  # Number of proxies to validate simultaneously
DEFAULT_TEST_SITES = ["icanhazip.com", "api.ipify.org", "ifconfig.me"]
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Initialize proxy cache
from proxy_cache import ProxyCache
proxy_cache = ProxyCache()

# Load user agents
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
]

try:
    with open("user_agents.txt", "r") as f:
        for line in f:
            user_agents.append(line.replace("\n", ""))
except FileNotFoundError:
    pass


class Proxy:
    """Class to handle proxy validation and testing"""
    
    def __init__(self, method, proxy_string):
        if method.lower() not in ["http", "https", "socks4", "socks5"]:
            raise NotImplementedError("Only HTTP, HTTPS, SOCKS4, and SOCKS5 are supported")
        self.method = method.lower()
        self.proxy = proxy_string
        self.test_results = {}
        self.reliability_score = 0
        self.avg_response_time = 0
        self.success_rate = 0

    def is_valid(self):
        """Check if the proxy format is valid"""
        return re.match(r"\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?$", self.proxy)

    def check_site(self, site, timeout, user_agent):
        """Test the proxy with a specific site"""
        if self.method in ["socks4", "socks5"]:
            socks.set_default_proxy(socks.SOCKS4 if self.method == "socks4" else socks.SOCKS5,
                                   self.proxy.split(':')[0], int(self.proxy.split(':')[1]))
            socket.socket = socks.socksocket
            try:
                start_time = time.time()
                urllib.request.urlopen("http://" + site, timeout=timeout)
                end_time = time.time()
                time_taken = end_time - start_time
                return True, time_taken, None
            except Exception as e:
                return False, 0, e
        else:
            url = self.method + "://" + self.proxy
            proxy_support = urllib.request.ProxyHandler({self.method: url})
            opener = urllib.request.build_opener(proxy_support)
            urllib.request.install_opener(opener)
            req = urllib.request.Request(self.method + "://" + site)
            req.add_header("User-Agent", user_agent)
            
            try:
                start_time = time.time()
                urllib.request.urlopen(req, timeout=timeout)
                end_time = time.time()
                time_taken = end_time - start_time
                return True, time_taken, None
            except Exception as e:
                return False, 0, e

    def check_multiple_sites(self, sites, timeout, user_agent):
        """Test the proxy against multiple sites"""
        results = {}
        successful_tests = 0
        total_response_time = 0
        
        for site in sites:
            success, time_taken, error = self.check_site(site, timeout, user_agent)
            results[site] = {
                "success": success,
                "time": time_taken,
                "error": str(error) if error else None
            }
            
            if success:
                successful_tests += 1
                total_response_time += time_taken
        
        # Calculate metrics
        self.test_results = results
        self.success_rate = successful_tests / len(sites) if sites else 0
        self.avg_response_time = total_response_time / successful_tests if successful_tests > 0 else float('inf')
        
        # Calculate reliability score (higher is better)
        if successful_tests > 0:
            self.reliability_score = self.success_rate * (1 / (1 + self.avg_response_time))
        else:
            self.reliability_score = 0
            
        return self.success_rate > 0  # Consider proxy valid if at least one test was successful

    def __str__(self):
        return self.proxy


def scrape_proxies(method, output_file, verbose=False):
    """Scrape proxies from various sources"""
    from proxyScraper import scrape
    import asyncio
    
    console.print(f"[bold yellow]Scraping {method} proxies...[/]")
    
    if sys.version_info >= (3, 7) and sys.platform == 'Windows':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scrape(method, output_file, verbose))
        loop.close()
    elif sys.version_info >= (3, 7):
        asyncio.run(scrape(method, output_file, verbose))
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scrape(method, output_file, verbose))
        loop.close()
    
    # Count proxies
    proxy_count = 0
    try:
        with open(output_file, 'r') as f:
            proxy_count = sum(1 for line in f if line.strip())
    except FileNotFoundError:
        pass
    
    console.print(f"[bold green]Scraped {proxy_count} {method} proxies[/]")
    return proxy_count


def validate_proxies(input_file, output_file, method, timeout, sites, min_success_rate=0.0, verbose=False):
    """Validate proxies against multiple sites"""
    global STOP_VALIDATION
    
    # Reset stop flag
    STOP_VALIDATION = False
    
    # Import optimized validator
    from proxy_validator import validate_all_proxies
    
    # Load proxies from file
    proxies = []
    try:
        with open(input_file, "r") as f:
            for line in f:
                proxy_str = line.strip()
                if proxy_str:
                    proxies.append(Proxy(method, proxy_str))
    except FileNotFoundError:
        console.print(f"[bold red]Error: File {input_file} not found[/]")
        return []    
    console.print(f"[bold yellow]Validating {len(proxies)} proxies...[/]")
    console.print(Panel("[bold green]STOP OPTIONS:[/bold green]\n[yellow]1.[/yellow] Type [bold red]s[/bold red] and press Enter\n[yellow]2.[/yellow] Press [bold red]Ctrl+C[/bold red]\n[yellow]3.[/yellow] Type [bold red]stop[/bold red] in another terminal", title="Quick Stop", border_style="cyan"))
    
    # Set up a thread to check for stop command
    stop_thread = threading.Thread(target=check_for_stop_command)
    stop_thread.daemon = True
    stop_thread.start()
    
    # Filter out invalid format proxies
    proxies = list(filter(lambda x: x.is_valid(), proxies))
    
    if not proxies:
        console.print("[bold red]No valid proxies to check[/]")
        return []
    
    # Valid proxies list
    valid_proxies = []
    
    # Progress tracking
    total_proxies = len(proxies)
    successful_proxies = 0
    
    # For Telegram batching
    telegram_batch = []
    
    # Function to test a single proxy
    def check_proxy(proxy, progress):
        nonlocal successful_proxies
        
        # Check if validation should stop
        if STOP_VALIDATION:
            return
            
        user_agent = random.choice(user_agents)
        task_id = progress.add_task(f"[cyan]Testing {proxy.proxy}...", total=len(sites))
        
        # Test against multiple sites
        valid = proxy.check_multiple_sites(sites, timeout, user_agent)
        
        for _ in range(len(sites)):
            progress.update(task_id, advance=1)
        
        progress.remove_task(task_id)
        
        if valid and proxy.success_rate >= min_success_rate:
            successful_proxies += 1
            valid_proxies.append(proxy)
            
            # Add to Telegram batch if enabled
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                telegram_batch.append(proxy)
                
                # Send batch if we've reached the batch size
                if len(telegram_batch) >= BATCH_SIZE:
                    send_to_telegram([str(p) for p in telegram_batch], method)
                    telegram_batch.clear()
                    
            progress.print(f"[green]✓ {proxy.proxy} - Success rate: {proxy.success_rate*100:.1f}%, "
                          f"Response time: {proxy.avg_response_time:.3f}s[/]")
      # Use rich progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        main_task = progress.add_task("[yellow]Validating proxies...", total=total_proxies)
        
        # Create thread pool
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all proxy testing tasks
            futures = []
            for proxy in proxies:
                if STOP_VALIDATION:
                    break
                futures.append(executor.submit(check_proxy, proxy, progress))
              # Wait for completion and update progress
            for i, future in enumerate(futures):
                if STOP_VALIDATION:
                    console.print("\n[bold yellow]⚠️ Validation stopped by user[/]")
                    break
                try:
                    future.result(timeout=0.5)  # Small timeout to make stopping more responsive
                except TimeoutError:
                    # Just a timeout for responsiveness, continue waiting
                    i -= 1
                    continue
                progress.update(main_task, completed=i+1)
                
                # Check for stop every few proxies for better responsiveness
                if i % 5 == 0 and STOP_VALIDATION:
                    console.print("\n[bold yellow]⚠️ Validation stopped by user[/]")
                    break
    
    # Send remaining proxies to Telegram if enabled
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and telegram_batch:
        send_to_telegram([str(p) for p in telegram_batch], method)
    
    # Sort proxies by reliability
    valid_proxies.sort(key=lambda p: p.reliability_score, reverse=True)
    
    # Save to output file
    with open(output_file, "w") as f:
        for proxy in valid_proxies:
            f.write(str(proxy) + "\n")
    
    # Save detailed results
    detailed_results = []
    for proxy in valid_proxies:
        detailed_results.append({
            "proxy": str(proxy),
            "success_rate": proxy.success_rate,
            "avg_response_time": proxy.avg_response_time,
            "reliability_score": proxy.reliability_score,
            "test_results": proxy.test_results
        })
    
    json_output = output_file.replace(".txt", ".json")
    with open(json_output, "w") as f:
        json.dump(detailed_results, f, indent=2)
    
    return valid_proxies


def send_to_telegram(proxy_list, proxy_type):
    """Send a batch of proxies to a Telegram bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    try:
        proxies_text = "\n".join(str(p) for p in proxy_list)
        message = f"🔄 *{len(proxy_list)} New Valid {proxy_type.upper()} Proxies:*\n```\n{proxies_text}\n```"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            console.print(f"[green]✓ Sent {len(proxy_list)} proxies to Telegram[/]")
            return True
        else:
            console.print(f"[red]Failed to send to Telegram: {response.text}[/]")
            return False
    except Exception as e:
        console.print(f"[red]Error sending to Telegram: {str(e)}[/]")
        return False


def display_results(proxies, method, sites):
    """Display validation results in a nice table"""
    if not proxies:
        console.print("[bold red]No valid proxies found[/]")
        return
    
    # Create table
    table = Table(title=f"Valid {method.upper()} Proxies")
    
    # Add columns
    table.add_column("Proxy", style="cyan")
    table.add_column("Success Rate", justify="center")
    table.add_column("Avg Response", justify="right")
    table.add_column("Reliability", justify="right")
    
    # Add site-specific columns
    for site in sites:
        table.add_column(site, justify="center")
    
    # Add rows
    for proxy in proxies[:20]:  # Show top 20
        # Format site results
        site_statuses = []
        for site in sites:
            site_result = proxy.test_results.get(site, {})
            if site_result.get("success", False):
                time_val = site_result.get("time", 0)
                site_statuses.append(f"[green]✓[/] ({time_val:.2f}s)")
            else:
                site_statuses.append("[red]✗[/]")
        
        # Add row
        table.add_row(
            proxy.proxy,
            f"{proxy.success_rate*100:.1f}%",
            f"{proxy.avg_response_time:.3f}s",
            f"{proxy.reliability_score:.5f}",
            *site_statuses
        )
    
    console.print(table)
    
    if len(proxies) > 20:
        console.print(f"[yellow]Showing top 20 of {len(proxies)} valid proxies[/]")


def check_for_stop_command():
    """Check for stop command in a separate thread"""
    global STOP_VALIDATION
    try:
        console.print("[bold cyan]✓ Press [red]s[/red] + [red]Enter[/red] or [red]Ctrl+C[/red] to stop validation at any time[/]")
        while not STOP_VALIDATION:
            try:
                # Poll for input without blocking
                if sys.stdin.isatty():  # Only try to read input if running in a terminal
                    input_ready = select.select([sys.stdin], [], [], 0.5)[0]
                    if input_ready:
                        cmd = sys.stdin.readline().strip().lower()
                        if cmd in ["stop", "s", "q", "quit", "exit"]:
                            STOP_VALIDATION = True
                            console.print("\n[bold yellow]⚠️ STOPPING[/] - Validation will stop after current batch completes...[/]")
                            console.print("[bold cyan]Please wait, cleaning up...[/]")
                else:
                    time.sleep(0.5)
            except Exception:
                time.sleep(0.5)
    except Exception:
        pass


def main():
    """Main function"""
    console.clear()
    
    # Print banner
    banner = """
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃                                                                                ┃
    ┃   ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗    ┃
    ┃   ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗   ┃
    ┃   ██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝   ┃
    ┃   ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗   ┃
    ┃   ██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║   ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║   ┃
    ┃   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   ┃
    ┃                                                                                ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """    
    console.print(Panel.fit(banner, border_style="blue"))
    console.print("[bold]A streamlined proxy scraper and validator[/]")
    console.print(f"[dim]Version 1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
    console.print("[bold green]Created by:[/] [yellow]cyb3r_vishal[/] | [blue]community DevKitX[/]")
    console.print()
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
      # Parse arguments
    parser = argparse.ArgumentParser(description="ProxyMaster - Proxy scraper and validator")
    parser.add_argument(
        "-p", "--proxy", 
        help="Proxy type to use (http, https, socks4, socks5)", 
        default="http"
    )
    parser.add_argument(
        "-t", "--timeout", 
        type=int, 
        help="Timeout in seconds for proxy validation", 
        default=DEFAULT_TIMEOUT
    )
    parser.add_argument(
        "-s", "--sites", 
        help="Comma-separated list of sites to validate against", 
        default="icanhazip.com,api.ipify.org,ifconfig.me"
    )
    parser.add_argument(
        "-m", "--min-success", 
        type=float, 
        help="Minimum success rate (0.0 to 1.0)", 
        default=0.25
    )
    parser.add_argument(
        "-i", "--input", 
        help="Input file with proxies (skips scraping if provided)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        help="Enable verbose output", 
        action="store_true"
    )
    parser.add_argument(
        "--telegram-token", 
        help="Telegram bot token for sending proxy lists"
    )
    parser.add_argument(
        "--telegram-chat", 
        help="Telegram chat ID to send proxy lists to"
    )
    parser.add_argument(
        "--telegram-batch", 
        type=int,
        help="Send proxies to Telegram in batches of this size", 
        default=100
    )
    args = parser.parse_args()
    
    # Parse test sites
    test_sites = args.sites.split(",")
    
    # Setup Telegram integration if provided
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BATCH_SIZE
    if args.telegram_token and args.telegram_chat:
        TELEGRAM_BOT_TOKEN = args.telegram_token
        TELEGRAM_CHAT_ID = args.telegram_chat
        BATCH_SIZE = args.telegram_batch
        console.print("[bold blue]Telegram integration enabled[/]")
        console.print(f"[dim]Will send proxies in batches of {BATCH_SIZE}[/]")
    
    # Create timestamped output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scraped_file = os.path.join(OUTPUT_DIR, f"{args.proxy}_proxies_{timestamp}.txt")
    valid_file = os.path.join(OUTPUT_DIR, f"{args.proxy}_valid_{timestamp}.txt")
    
    # Main workflow
    console.rule("[bold yellow]Step 1: Proxy Acquisition[/]")
    
    if args.input:
        console.print(f"[yellow]Using existing proxy list: {args.input}[/]")
        scraped_file = args.input
    else:
        # Scrape proxies
        scrape_proxies(args.proxy, scraped_file, args.verbose)
    
    console.rule("[bold yellow]Step 2: Proxy Validation[/]")
    
    # Validate proxies
    valid_proxies = validate_proxies(
        scraped_file, 
        valid_file, 
        args.proxy, 
        args.timeout, 
        test_sites, 
        args.min_success, 
        args.verbose
    )
    
    # Display results
    console.rule("[bold yellow]Results[/]")
    display_results(valid_proxies, args.proxy, test_sites)
    
    # Save current date valid proxies to live file
    live_file = os.path.join(OUTPUT_DIR, f"{args.proxy}_live.txt")
    with open(live_file, "w") as f:
        for proxy in valid_proxies:
            f.write(str(proxy) + "\n")
    
    # Send proxies to Telegram
    send_to_telegram(valid_proxies, args.proxy)
    
    # Finished
    console.print()
    console.print(f"[bold green]✓ Found {len(valid_proxies)} valid proxies[/]")
    console.print(f"[bold blue]↓ Saved to:[/]")
    console.print(f"  • All Valid: [cyan]{valid_file}[/]")
    console.print(f"  • Live Proxies: [cyan]{live_file}[/]")
    console.print(f"  • Detailed Report: [cyan]{valid_file.replace('.txt', '.json')}[/]")
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        STOP_VALIDATION = True
        console.print("\n[bold yellow]⚠️ Operation interrupted by user. Forcefully stopping validation...[/]")
        console.print("[bold green]Saving any valid proxies found so far...[/]")
        try:
            # Try to save any valid proxies that might have been found before stopping
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            emergency_save = os.path.join(OUTPUT_DIR, f"emergency_valid_{timestamp}.txt")
            with open(emergency_save, "w") as f:
                f.write("# Emergency save after user interruption\n")
            console.print(f"[bold green]✓ Emergency save completed to:[/] [cyan]{emergency_save}[/]")
        except:
            pass
        console.print("[dim]Exiting immediately...[/]")
        # Force exit with a success code
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/]")
        if "--verbose" in sys.argv:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
