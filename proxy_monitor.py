#!/usr/bin/env python3
"""
Proxy Monitor - Automatic proxy re-checking tool
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
import threading
import schedule

# Check for required packages and install if missing
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
    import requests
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "requests", "schedule"])
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
    import requests
    import schedule

# Import from proxymaster for reuse
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from proxymaster import Proxy, validate_proxies, display_results

# Initialize console
console = Console()

# Default settings
DEFAULT_INTERVAL = 60  # minutes
DEFAULT_TEST_SITES = ["icanhazip.com", "api.ipify.org", "ifconfig.me"]
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def load_proxies(file_path, method):
    """Load proxies from file"""
    proxies = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                proxy_str = line.strip()
                if proxy_str:
                    proxies.append(Proxy(method, proxy_str))
    except FileNotFoundError:
        console.print(f"[bold red]Error: File {file_path} not found[/]")
    return proxies


def recheck_proxies(method, input_file, timeout, interval):
    """Re-check proxies and update the live list"""
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Test sites
    test_sites = DEFAULT_TEST_SITES
    
    # Load proxies
    console.print(f"[bold yellow]Loading proxies from {input_file}...[/]")
    proxies = load_proxies(input_file, method)
    
    if not proxies:
        console.print("[bold red]No proxies to check. Exiting.[/]")
        return
    
    # Create timestamped output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    valid_file = os.path.join(OUTPUT_DIR, f"{method}_verified_{timestamp}.txt")
    
    # Validate proxies
    console.print(f"[bold yellow]Re-checking {len(proxies)} proxies...[/]")
    valid_proxies = validate_proxies(
        input_file, 
        valid_file, 
        method, 
        timeout, 
        test_sites,
        min_success_rate=0.25,
        verbose=False
    )
    
    # Update live file
    live_file = os.path.join(OUTPUT_DIR, f"{method}_live.txt")
    with open(live_file, "w") as f:
        for proxy in valid_proxies:
            f.write(str(proxy) + "\n")
    
    # Display results
    display_results(valid_proxies, method, test_sites)
    
    # Log status
    console.print()
    console.print(f"[bold green]✓ Found {len(valid_proxies)} valid proxies[/]")
    console.print(f"[bold blue]↓ Updated files:[/]")
    console.print(f"  • Live Proxies: [cyan]{live_file}[/]")
    console.print(f"  • Latest Check: [cyan]{valid_file}[/]")
    
    # Save history record
    history_file = os.path.join(OUTPUT_DIR, f"{method}_history.json")
    history_data = []
    
    # Load existing history if available
    try:
        with open(history_file, "r") as f:
            history_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    # Add new entry
    history_data.append({
        "timestamp": timestamp,
        "datetime": datetime.now().isoformat(),
        "total_checked": len(proxies),
        "valid_count": len(valid_proxies),
        "success_rate": len(valid_proxies) / len(proxies) if proxies else 0
    })
    
    # Save history
    with open(history_file, "w") as f:
        json.dump(history_data, f, indent=2)
    
    return valid_proxies


def run_scheduler(method, input_file, timeout, interval):
    """Run the scheduler for periodic checking"""
    console.print(f"[bold blue]Starting proxy monitor...[/]")
    console.print(f"[bold blue]Will check proxies every {interval} minutes[/]")
    
    # Define the job
    def job():
        console.rule(f"[bold yellow]Scheduled Proxy Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
        recheck_proxies(method, input_file, timeout, interval)
    
    # Schedule the job
    schedule.every(interval).minutes.do(job)
    
    # Run once immediately
    job()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold red]Monitor stopped by user[/]")


def main():
    """Main function"""
    console.clear()
    
    # Print banner
    banner = """
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃                                                                          ┃
    ┃   ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗   ███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗     ┃
    ┃   ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝   ████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗    ┃
    ┃   ██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝    ██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝    ┃
    ┃   ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝     ██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗    ┃
    ┃   ██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║      ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║    ┃
    ┃   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝      ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝    ┃
    ┃                                                                          ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """    
    console.print(Panel.fit(banner, border_style="blue"))
    console.print("[bold]Automatic proxy monitoring and refreshing[/]")
    console.print(f"[dim]Version 1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
    console.print("[bold green]Created by:[/] [yellow]cyb3r_vishal[/] | [blue]community DevKitX[/]")
    console.print()
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Proxy Monitor - Automatic proxy re-checking tool")
    parser.add_argument(
        "-p", "--proxy", 
        help="Proxy type to monitor (http, https, socks4, socks5)", 
        default="http"
    )
    parser.add_argument(
        "-i", "--input", 
        help="Input file with proxies to monitor", 
        default=os.path.join(OUTPUT_DIR, "http_live.txt")
    )
    parser.add_argument(
        "-t", "--timeout", 
        type=int, 
        help="Timeout in seconds for proxy validation", 
        default=10
    )
    parser.add_argument(
        "-n", "--interval", 
        type=int, 
        help="Check interval in minutes", 
        default=DEFAULT_INTERVAL
    )
    parser.add_argument(
        "--once", 
        help="Run once and exit (don't run as a service)", 
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # If input file not specified, use default for the proxy type
    if args.input == os.path.join(OUTPUT_DIR, "http_live.txt") and args.proxy != "http":
        args.input = os.path.join(OUTPUT_DIR, f"{args.proxy}_live.txt")
    
    # Run once or as a service
    if args.once:
        console.rule("[bold yellow]One-time Proxy Check[/]")
        recheck_proxies(args.proxy, args.input, args.timeout, args.interval)
    else:
        run_scheduler(args.proxy, args.input, args.timeout, args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/]")
        if "--verbose" in sys.argv:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
