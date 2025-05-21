#!/usr/bin/env python3
"""
Proxy Rotator - Intelligent proxy rotation utility
"""

import argparse
import json
import os
import random
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import http.client
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

# Check for required packages and install if missing
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.table import Table
    import requests
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "requests"])
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.table import Table
    import requests

# Initialize console
console = Console()

# Default settings
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
DEFAULT_PORT = 8080
DEFAULT_ROTATION = 20  # requests before rotation
DEFAULT_TIMEOUT = 10   # seconds
DEFAULT_TEST_URL = "http://icanhazip.com/"


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler that forwards requests through a rotating proxy"""
    
    server_version = "ProxyRotator/1.0"
    protocol_version = "HTTP/1.1"
    timeout = DEFAULT_TIMEOUT
    
    def do_GET(self):
        self.process_request("GET")
        
    def do_POST(self):
        self.process_request("POST")
        
    def do_HEAD(self):
        self.process_request("HEAD")
        
    def do_PUT(self):
        self.process_request("PUT")
        
    def do_DELETE(self):
        self.process_request("DELETE")
        
    def do_OPTIONS(self):
        self.process_request("OPTIONS")
    
    def process_request(self, method):
        """Process and forward HTTP request through a proxy"""
        self.server.request_count += 1
        
        # Rotate proxy if needed
        if self.server.request_count >= self.server.rotation_count:
            self.server.rotate_proxy()
            self.server.request_count = 0
        
        # Parse request URL
        url = urllib.parse.urlparse(self.path)
        
        # Build destination address
        netloc = url.netloc or url.path
        if not netloc:
            self.send_error(400, "Bad Request: Missing URL")
            return
        
        if url.scheme:
            dest_addr = netloc
            dest_path = url.path
            if url.params:
                dest_path += ";" + url.params
            if url.query:
                dest_path += "?" + url.query
        else:
            dest_addr = netloc
            dest_path = "/"
        
        dest_port = 80
        if ":" in dest_addr:
            dest_addr, port_str = dest_addr.split(":", 1)
            try:
                dest_port = int(port_str)
            except ValueError:
                self.send_error(400, "Bad Request: Invalid port")
                return
        
        # Get current proxy
        proxy_info = self.server.current_proxy
        
        # Log the request
        console.print(f"[dim][{datetime.now().strftime('%H:%M:%S')}] {method} {self.path} via {proxy_info['proxy']}[/]")
        
        # Handle headers
        headers = {}
        for key, val in self.headers.items():
            if key.lower() not in ('connection', 'proxy-connection', 'keep-alive', 'proxy-authorization', 'te', 'trailers', 'upgrade'):
                headers[key] = val
        
        # Prepare connection to proxy
        proxy_parts = proxy_info["proxy"].split(":")
        proxy_host = proxy_parts[0]
        proxy_port = int(proxy_parts[1])
        
        try:
            # Connect to proxy
            connection = http.client.HTTPConnection(proxy_host, proxy_port, timeout=self.timeout)
            
            # Read request body for methods that have one
            body = None
            if method in ("POST", "PUT"):
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length else None
            
            # Send request through proxy
            full_url = f"http://{dest_addr}:{dest_port}{dest_path}"
            connection.request(method, full_url, body=body, headers=headers)
            
            # Get response
            response = connection.getresponse()
            
            # Send response headers
            self.send_response(response.status)
            for key, val in response.getheaders():
                if key.lower() not in ('connection', 'proxy-connection', 'keep-alive', 'proxy-authorization', 'transfer-encoding'):
                    self.send_header(key, val)
            self.end_headers()
            
            # Send response body
            self.wfile.write(response.read())
            
            # Close connection
            connection.close()
            
            # Update proxy stats
            self.server.successful_requests += 1
            proxy_info["success_count"] += 1
            
        except Exception as e:
            # Handle errors
            console.print(f"[red]Error for {proxy_info['proxy']}: {str(e)}[/]")
            self.send_error(502, f"Bad Gateway: {str(e)}")
            
            # Mark proxy as failed
            proxy_info["fail_count"] += 1
            
            # Rotate proxy if it fails too much
            if proxy_info["fail_count"] >= 3:
                console.print(f"[red]Proxy {proxy_info['proxy']} failed too many times, rotating...[/]")
                self.server.rotate_proxy()
    
    def log_message(self, format, *args):
        """Override logging to use our rich console"""
        return


class RotatingProxyServer(HTTPServer):
    """HTTP server with proxy rotation capabilities"""
    
    def __init__(self, server_address, RequestHandlerClass, proxies, rotation_count):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.proxies = proxies
        self.rotation_count = rotation_count
        self.current_proxy_index = 0
        self.current_proxy = proxies[0]
        self.request_count = 0
        self.successful_requests = 0
        self.total_requests = 0
        self.rotation_count = rotation_count
        self.last_rotation = datetime.now()
        
        # Add stats to proxies
        for proxy in self.proxies:
            proxy["success_count"] = 0
            proxy["fail_count"] = 0
    
    def rotate_proxy(self):
        """Rotate to next proxy in the list"""
        # Update stats
        elapsed = (datetime.now() - self.last_rotation).total_seconds()
        
        # Log rotation
        if self.request_count > 0:
            console.print(f"[yellow]Rotating proxy after {self.request_count} requests ({elapsed:.1f} seconds)[/]")
        
        # Get next proxy or best performing one
        if random.random() < 0.8:  # 80% chance to use next in sequence
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        else:  # 20% chance to use best performing proxy
            best_index = 0
            best_score = -1
            for i, proxy in enumerate(self.proxies):
                success = proxy["success_count"]
                fail = proxy["fail_count"]
                # Simple scoring formula
                score = success - (fail * 2)
                if score > best_score:
                    best_score = score
                    best_index = i
            self.current_proxy_index = best_index
        
        # Update current proxy
        self.current_proxy = self.proxies[self.current_proxy_index]
        self.last_rotation = datetime.now()
        
        # Log new proxy
        console.print(f"[green]Now using proxy: {self.current_proxy['proxy']}[/]")


def load_proxies(proxy_file):
    """Load and validate proxies from file"""
    proxy_list = []
    
    try:
        # Check if JSON file (for geo data)
        if proxy_file.endswith('.json'):
            with open(proxy_file, 'r') as f:
                data = json.load(f)
                # Extract proxies from JSON format
                for item in data:
                    if isinstance(item, dict) and 'proxy' in item:
                        proxy_list.append({
                            "proxy": item["proxy"],
                            "country": item.get("country", "Unknown"),
                            "city": item.get("city", "Unknown"),
                            "isp": item.get("isp", "Unknown"),
                            "anonymity": item.get("anonymityLevel", "Unknown"),
                        })
        else:
            # Regular text file with proxies
            with open(proxy_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Check for comment with details
                    parts = line.split('#', 1)
                    proxy = parts[0].strip()
                    details = parts[1].strip() if len(parts) > 1 else ""
                    
                    proxy_list.append({
                        "proxy": proxy,
                        "details": details
                    })
    except Exception as e:
        console.print(f"[bold red]Error loading proxies: {str(e)}[/]")
        sys.exit(1)
    
    if not proxy_list:
        console.print("[bold red]No proxies found in the input file[/]")
        sys.exit(1)
    
    return proxy_list


def test_proxies(proxies, timeout):
    """Test proxies before starting the server"""
    console.print(f"[bold yellow]Testing {len(proxies)} proxies...[/]")
    
    working_proxies = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("[cyan]Testing proxies...", total=len(proxies))
        
        for proxy_info in proxies:
            proxy_str = proxy_info["proxy"]
            progress.update(task, description=f"[cyan]Testing {proxy_str}...")
            
            try:
                proxy_dict = {
                    'http': f'http://{proxy_str}',
                    'https': f'http://{proxy_str}'
                }
                
                response = requests.get(DEFAULT_TEST_URL, proxies=proxy_dict, timeout=timeout)
                
                if response.status_code == 200:
                    working_proxies.append(proxy_info)
                    progress.print(f"[green]✓ {proxy_str} is working[/]")
                else:
                    progress.print(f"[red]✗ {proxy_str} returned status {response.status_code}[/]")
            except Exception as e:
                progress.print(f"[red]✗ {proxy_str} failed: {str(e)}[/]")
            
            progress.update(task, advance=1)
    
    console.print(f"[bold green]Found {len(working_proxies)} working proxies[/]")
    return working_proxies


def run_proxy_server(port, proxies, rotation_count, timeout):
    """Run the rotating proxy server"""
    # Update timeout in handler
    ProxyHandler.timeout = timeout
    
    server = RotatingProxyServer(('localhost', port), ProxyHandler, proxies, rotation_count)
    
    console.print(f"[bold green]Starting proxy rotator on port {port}[/]")
    console.print(f"[bold green]Using {len(proxies)} proxies with rotation every {rotation_count} requests[/]")
    console.print("[yellow]Use this proxy server at:[/] [bold]http://localhost:{port}[/]")
    console.print("[dim]Press Ctrl+C to stop the server[/]")
    
    # Start a thread to display stats periodically
    stop_event = threading.Event()
    
    def show_stats():
        last_total = 0
        start_time = time.time()
        
        while not stop_event.is_set():
            time.sleep(10)  # Update every 10 seconds
            
            # Calculate requests per second
            current_total = server.successful_requests
            elapsed = time.time() - start_time
            requests_per_sec = current_total / elapsed if elapsed > 0 else 0
            
            # Calculate current throughput
            current_throughput = (current_total - last_total) / 10  # requests per second in last interval
            last_total = current_total
            
            # Display stats
            console.print(f"[bold blue]------- Stats -------[/]")
            console.print(f"Successful requests: {server.successful_requests}")
            console.print(f"Throughput: {current_throughput:.1f} req/s (current), {requests_per_sec:.1f} req/s (average)")
            console.print(f"Current proxy: {server.current_proxy['proxy']}")
            
            # Show proxy performance
            table = Table(title="Proxy Performance")
            table.add_column("Proxy", style="cyan")
            table.add_column("Success", style="green", justify="right")
            table.add_column("Fails", style="red", justify="right")
            table.add_column("Success Rate", justify="right")
            
            for proxy in server.proxies:
                success = proxy["success_count"]
                fail = proxy["fail_count"]
                total = success + fail
                rate = (success / total) * 100 if total > 0 else 0
                
                table.add_row(
                    proxy["proxy"],
                    str(success),
                    str(fail),
                    f"{rate:.1f}%"
                )
            
            console.print(table)
    
    # Start stats thread
    stats_thread = threading.Thread(target=show_stats)
    stats_thread.daemon = True
    stats_thread.start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop_event.set()
        console.print("\n[bold red]Stopping server...[/]")
    finally:
        server.server_close()


def main():
    """Main function"""
    console.clear()
    
    # Print banner
    banner = """
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃                                                                                            ┃
    ┃   ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗    ██████╗  ██████╗ ████████╗ █████╗ ████████╗ ██████╗ ██████╗     ┃
    ┃   ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗    ┃
    ┃   ██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝     ██████╔╝██║   ██║   ██║   ███████║   ██║   ██║   ██║██████╔╝    ┃
    ┃   ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝      ██╔══██╗██║   ██║   ██║   ██╔══██║   ██║   ██║   ██║██╔══██╗    ┃
    ┃   ██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║       ██║  ██║╚██████╔╝   ██║   ██║  ██║   ██║   ╚██████╔╝██║  ██║    ┃
    ┃   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝    ┃
    ┃                                                                                            ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """    
    console.print(Panel.fit(banner, border_style="blue"))
    console.print("[bold]Intelligent proxy rotation utility[/]")
    console.print(f"[dim]Version 1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]")
    console.print("[bold green]Created by:[/] [yellow]cyb3r_vishal[/] | [blue]community DevKitX[/]")
    console.print()
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Proxy Rotator - Intelligent proxy rotation utility")
    parser.add_argument(
        "-p", "--port", 
        type=int,
        help="Port to run the proxy server on", 
        default=DEFAULT_PORT
    )
    parser.add_argument(
        "-i", "--input", 
        help="Input file with proxies", 
        required=True
    )
    parser.add_argument(
        "-r", "--rotation", 
        type=int,
        help="Number of requests before rotating proxy", 
        default=DEFAULT_ROTATION
    )
    parser.add_argument(
        "-t", "--timeout", 
        type=int,
        help="Timeout in seconds for proxy requests", 
        default=DEFAULT_TIMEOUT
    )
    parser.add_argument(
        "--no-test", 
        help="Skip testing proxies before starting server", 
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # Load proxies
    console.rule("[bold yellow]Loading Proxies[/]")
    proxies = load_proxies(args.input)
    
    # Test proxies
    if not args.no_test:
        console.rule("[bold yellow]Testing Proxies[/]")
        proxies = test_proxies(proxies, args.timeout)
        
        if not proxies:
            console.print("[bold red]No working proxies found. Exiting.[/]")
            sys.exit(1)
    
    # Run server
    console.rule("[bold yellow]Starting Server[/]")
    run_proxy_server(args.port, proxies, args.rotation, args.timeout)


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
