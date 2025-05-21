#!/usr/bin/env python3
"""
Proxy Geo - Add geolocation data to proxy lists
"""

import argparse
import json
import os
import sys
from datetime import datetime
import concurrent.futures

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
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "requests"])
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
    import requests

# Initialize console
console = Console()

# Default settings
DEFAULT_API = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,isp,org,as,asname,proxy,hosting"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
BACKUP_API = "https://ipinfo.io/{ip}/json"  # Backup API service


def get_ip_info(ip, use_backup=False):
    """Get geolocation data for an IP address"""
    try:
        if use_backup:
            response = requests.get(BACKUP_API.format(ip=ip), timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Map ipinfo.io response to our standard format
                return {
                    "status": "success",
                    "country": data.get("country", "Unknown"),
                    "countryCode": data.get("country", "XX"),
                    "region": data.get("region", ""),
                    "regionName": data.get("region", ""),
                    "city": data.get("city", "Unknown"),
                    "isp": data.get("org", "Unknown"),
                    "org": data.get("org", ""),
                    "as": data.get("asn", ""),
                    "asname": data.get("asn", ""),
                    "proxy": "Unknown",
                    "hosting": "Unknown"
                }
        else:
            response = requests.get(DEFAULT_API.format(ip=ip), timeout=5)
            if response.status_code == 200:
                return response.json()
        
        # If we get here, something went wrong
        return {
            "status": "fail",
            "country": "Unknown",
            "countryCode": "XX",
            "city": "Unknown",
            "isp": "Unknown",
            "proxy": "Unknown",
            "hosting": "Unknown"
        }
    except Exception as e:
        # Handle any exceptions
        return {
            "status": "error",
            "message": str(e),
            "country": "Unknown",
            "countryCode": "XX",
            "city": "Unknown",
            "isp": "Unknown",
            "proxy": "Unknown",
            "hosting": "Unknown"
        }


def assess_anonymity(ip_info):
    """Assess the anonymity level of a proxy based on IP data"""
    if ip_info["status"] != "success":
        return "Unknown"
    
    # Check if explicitly marked as proxy
    if ip_info.get("proxy", False):
        # Check for hosting vs residential
        if ip_info.get("hosting", False):
            return "Data Center (Medium)"
        else:
            return "Residential (High)"
    
    # Check organization/ISP for keywords
    org = (ip_info.get("org", "") or "").lower()
    isp = (ip_info.get("isp", "") or "").lower()
    asname = (ip_info.get("asname", "") or "").lower()
    
    hosting_keywords = ["hosting", "cloud", "server", "data center", "datacenter", "vps", "dedicated"]
    residential_keywords = ["residential", "home", "broadband", "consumer", "telecom"]
    
    # Look for hosting keywords
    for keyword in hosting_keywords:
        if keyword in org or keyword in isp or keyword in asname:
            return "Data Center (Medium)"
    
    # Look for residential keywords
    for keyword in residential_keywords:
        if keyword in org or keyword in isp or keyword in asname:
            return "Residential (High)"
    
    # Default case
    return "Unknown"


def process_proxy_list(input_file, output_file):
    """Process a list of proxies, adding geolocation data"""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load proxies
    proxies = []
    try:
        with open(input_file, "r") as f:
            for line in f:
                proxy = line.strip()
                if proxy:
                    proxies.append(proxy)
    except FileNotFoundError:
        console.print(f"[bold red]Error: File {input_file} not found[/]")
        return False
    
    if not proxies:
        console.print("[bold red]No proxies found in input file[/]")
        return False
    
    # Prepare results list
    results = []
    
    # Function to process a single proxy
    def process_proxy(proxy):
        # Extract IP address from proxy string
        ip = proxy.split(":")[0]
        
        # Fetch geolocation data
        ip_info = get_ip_info(ip)
        
        # If primary API fails, try backup
        if ip_info["status"] != "success":
            ip_info = get_ip_info(ip, use_backup=True)
        
        # Assess anonymity
        anonymity = assess_anonymity(ip_info)
        
        # Create result entry
        return {
            "proxy": proxy,
            "ip": ip,
            "country": ip_info.get("country", "Unknown"),
            "countryCode": ip_info.get("countryCode", "XX"),
            "region": ip_info.get("regionName", ""),
            "city": ip_info.get("city", "Unknown"),
            "isp": ip_info.get("isp", "Unknown"),
            "organization": ip_info.get("org", ""),
            "as": ip_info.get("as", ""),
            "asname": ip_info.get("asname", ""),
            "isProxy": ip_info.get("proxy", False),
            "isHosting": ip_info.get("hosting", False),
            "anonymityLevel": anonymity
        }
    
    # Process proxies with progress bar
    console.print(f"[bold yellow]Processing {len(proxies)} proxies...[/]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Fetching geolocation data...", total=len(proxies))
        
        # Use thread pool for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_proxy = {executor.submit(process_proxy, proxy): proxy for proxy in proxies}
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    data = future.result()
                    results.append(data)
                    progress.update(task, advance=1)
                    
                    # Print info for completed proxy
                    proxy_str = f"{proxy} ({data['country']} - {data['city']})"
                    progress.print(f"[green]✓ {proxy_str}[/]")
                except Exception as e:
                    progress.print(f"[red]✗ {proxy} - Error: {str(e)}[/]")
                    progress.update(task, advance=1)
    
    # Sort by country and city
    results.sort(key=lambda x: (x["country"], x["city"]))
    
    # Save the results to JSON
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Also save a simplified text file with format: IP:PORT # Country - City (ISP) [Anonymity]
    text_output = output_file.replace(".json", ".txt")
    with open(text_output, "w") as f:
        for entry in results:
            f.write(f"{entry['proxy']} # {entry['country']} - {entry['city']} ({entry['isp']}) [{entry['anonymityLevel']}]\n")
    
    # Display statistics
    country_counts = {}
    anonymity_counts = {}
    
    for entry in results:
        country = entry["country"]
        anonymity = entry["anonymityLevel"]
        
        country_counts[country] = country_counts.get(country, 0) + 1
        anonymity_counts[anonymity] = anonymity_counts.get(anonymity, 0) + 1
    
    # Show country table
    table = Table(title="Proxy Distribution by Country")
    table.add_column("Country", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right")
    
    for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(results)) * 100
        table.add_row(country, str(count), f"{percentage:.1f}%")
    
    console.print(table)
    
    # Show anonymity table
    table = Table(title="Proxy Distribution by Anonymity Level")
    table.add_column("Anonymity Level", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right")
    
    for level, count in sorted(anonymity_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(results)) * 100
        table.add_row(level, str(count), f"{percentage:.1f}%")
    
    console.print(table)
    
    # Summary
    console.print()
    console.print(f"[bold green]✓ Processed {len(results)} proxies[/]")
    console.print(f"[bold blue]Output files:[/]")
    console.print(f"  • Detailed (JSON): [cyan]{output_file}[/]")
    console.print(f"  • Simplified (Text): [cyan]{text_output}[/]")
    
    return True


def main():
    """Main function"""
    console.clear()
    
    # Print banner
    banner = """
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃                                                                      ┃
    ┃   ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗       ██████╗ ███████╗ ██████╗      ┃
    ┃   ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝      ██╔════╝ ██╔════╝██╔═══██╗     ┃
    ┃   ██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ █████╗██║  ███╗█████╗  ██║   ██║     ┃
    ┃   ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  ╚════╝██║   ██║██╔══╝  ██║   ██║     ┃
    ┃   ██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║         ╚██████╔╝███████╗╚██████╔╝     ┃
    ┃   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝          ╚═════╝ ╚══════╝ ╚═════╝      ┃
    ┃                                                                      ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """    
    console.print(Panel.fit(banner, border_style="blue"))
    console.print("[bold]Add geolocation data to proxy lists[/]")
    console.print(f"[dim]Version 1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
    console.print("[bold green]Created by:[/] [yellow]cyb3r_vishal[/] | [blue]community DevKitX[/]")
    console.print()
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Proxy Geo - Add geolocation data to proxy lists")
    parser.add_argument(
        "-i", "--input", 
        help="Input file with proxies", 
        required=True
    )
    parser.add_argument(
        "-o", "--output", 
        help="Output JSON file with geolocation data", 
        default=None
    )
    
    args = parser.parse_args()
    
    # If output file not specified, create one based on input file
    if args.output is None:
        input_basename = os.path.basename(args.input)
        output_basename = input_basename.replace(".txt", "_geo.json")
        args.output = os.path.join(OUTPUT_DIR, output_basename)
    
    # Process proxy list
    console.rule("[bold yellow]Processing Proxies[/]")
    process_proxy_list(args.input, args.output)


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
