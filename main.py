#!/usr/bin/env python3
"""
ProxyScraper CLI — Scrape, validate, and export 100% live proxies.

Usage:
    python main.py                        # Scrape + validate HTTP proxies
    python main.py -p socks5              # Scrape + validate SOCKS5
    python main.py -p https -o out.txt    # Custom output file
    python main.py -i raw.txt -p http     # Validate proxies from a file
    python main.py --list-sources         # Show all proxy sources
    python main.py -p http --timeout 8    # Custom timeout
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from scraper import SOURCES, scrape
from checker import check_all, ProxyResult

console = Console()

BANNER = r"""
 ____                       ____                                
|  _ \ _ __ _____  ___   _ / ___|  ___ _ __ __ _ _ __   ___ _ __ 
| |_) | '__/ _ \ \/ / | | |\___ \ / __| '__/ _` | '_ \ / _ \ '__|
|  __/| | | (_) >  <| |_| | ___) | (__| | | (_| | |_) |  __/ |   
|_|   |_|  \___/_/\_\\__, ||____/ \___|_|  \__,_| .__/ \___|_|   
                      |___/                      |_|              
"""

VERSION = "2.0.0"


def print_banner():
    console.print(
        Panel.fit(
            f"[bold cyan]{BANNER}[/]\n"
            f"  [dim]v{VERSION}  •  CLI Proxy Scraper & Validator[/]\n"
            f"  [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]\n"
            f"  [bold green]by[/] [yellow]cyb3r_vishal[/] [dim]|[/] [blue]community DevKitX[/]",
            border_style="blue",
        )
    )


def list_sources():
    """Print all proxy sources grouped by type."""
    for proto, urls in SOURCES.items():
        table = Table(title=f"{proto.upper()} Sources", show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("URL", style="cyan")
        for i, url in enumerate(urls, 1):
            table.add_row(str(i), url)
        console.print(table)
        console.print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proxyscraper",
        description="Scrape and validate 100%% live proxies from the CLI.",  # noqa: argparse needs %%
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py -p http\n"
            "  python main.py -p socks5 -o socks5_live.txt\n"
            "  python main.py -i raw_proxies.txt -p http\n"
            "  python main.py --list-sources\n"
        ),
    )

    parser.add_argument(
        "-p", "--proto",
        choices=["http", "https", "socks4", "socks5"],
        default="http",
        help="Proxy protocol (default: http)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file for live proxies (default: output/<proto>_live.txt)",
    )
    parser.add_argument(
        "-i", "--input",
        default=None,
        help="Input file of proxies to validate (skips scraping)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=6,
        help="Timeout per proxy check in seconds (default: 6)",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Also save detailed JSON results",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Show all scraping sources and exit",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (just results)",
    )

    return parser


def load_proxies_from_file(filepath: str) -> list[str]:
    """Read proxies from a text file (one per line)."""
    if not os.path.isfile(filepath):
        console.print(f"[bold red]Error:[/] File not found: {filepath}")
        sys.exit(1)

    proxies = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)

    return proxies


def display_results(results: list[ProxyResult]):
    """Show live proxies in a rich table."""
    if not results:
        console.print("[bold red]No live proxies found.[/]")
        return

    table = Table(title=f"Live Proxies ({len(results)})", show_lines=False)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Proxy", style="cyan bold")
    table.add_column("Protocol", style="magenta", justify="center")
    table.add_column("Response", style="green", justify="right")
    table.add_column("IP Returned", style="yellow")
    table.add_column("Checks", justify="center")

    for i, r in enumerate(results[:50], 1):
        table.add_row(
            str(i),
            r.proxy,
            r.proto.upper(),
            f"{r.response_time:.2f}s",
            r.ip_returned or "-",
            f"[green]{r.checks_passed}/{r.checks_total}[/]",
        )

    console.print(table)

    if len(results) > 50:
        console.print(f"[dim]  ... and {len(results) - 50} more (see output file)[/]")


def save_results(
    results: list[ProxyResult], output_file: str, save_json: bool
):
    """Write live proxies to txt (and optionally JSON)."""
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    with open(output_file, "w") as f:
        for r in results:
            f.write(r.proxy + "\n")

    console.print(f"[bold green]Saved {len(results)} live proxies to:[/] [cyan]{output_file}[/]")

    if save_json:
        json_file = output_file.rsplit(".", 1)[0] + ".json"
        data = [
            {
                "proxy": r.proxy,
                "protocol": r.proto,
                "response_time": r.response_time,
                "ip_returned": r.ip_returned,
                "checks_passed": r.checks_passed,
                "checks_total": r.checks_total,
            }
            for r in results
        ]
        with open(json_file, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[bold green]JSON report:[/] [cyan]{json_file}[/]")


async def run(args):
    """Main async workflow: scrape → validate → save."""
    import checker
    checker.TIMEOUT_SECONDS = args.timeout

    proto = args.proto

    # ── Step 1: Acquire proxies ──────────────────────────────────────────
    if args.input:
        console.rule("[bold yellow]Step 1: Loading proxies from file[/]")
        raw_proxies = load_proxies_from_file(args.input)
        console.print(f"  Loaded [cyan]{len(raw_proxies)}[/] proxies from {args.input}")
    else:
        console.rule("[bold yellow]Step 1: Scraping proxies[/]")
        with console.status(f"[bold green]Scraping {proto.upper()} proxies from {len(SOURCES[proto])} sources..."):
            raw_proxies = await scrape(proto)
        console.print(f"  Scraped [cyan]{len(raw_proxies)}[/] unique {proto.upper()} proxies")

    if not raw_proxies:
        console.print("[bold red]No proxies found. Exiting.[/]")
        return

    # ── Step 2: Validate proxies ─────────────────────────────────────────
    console.rule("[bold yellow]Step 2: Validating proxies (100% live check)[/]")
    console.print(f"  Testing each proxy against [cyan]{3 if proto != 'https' else 4}[/] endpoints")
    console.print(f"  Timeout: [cyan]{args.timeout}s[/]  •  Concurrency: [cyan]100[/]  •  Batch: [cyan]200[/]")
    console.print()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
    )

    live_count = 0
    start_time = time.monotonic()

    with progress:
        task = progress.add_task(
            f"[cyan]Checking {proto.upper()} proxies", total=len(raw_proxies)
        )

        def on_progress(checked: int, total: int, result: ProxyResult):
            nonlocal live_count
            if result.alive:
                live_count += 1
                progress.update(
                    task,
                    completed=checked,
                    description=(
                        f"[cyan]Checking {proto.upper()} proxies "
                        f"[green]({live_count} live)[/]"
                    ),
                )
            else:
                progress.update(task, completed=checked)

        live_results = await check_all(raw_proxies, proto, on_progress=on_progress)

    elapsed = time.monotonic() - start_time

    # ── Step 3: Results ──────────────────────────────────────────────────
    console.rule("[bold yellow]Results[/]")
    console.print(
        f"  Checked: [cyan]{len(raw_proxies)}[/]  •  "
        f"Live: [bold green]{len(live_results)}[/]  •  "
        f"Dead: [red]{len(raw_proxies) - len(live_results)}[/]  •  "
        f"Time: [dim]{elapsed:.1f}s[/]"
    )
    console.print()

    if not live_results:
        console.print("[bold red]No proxies passed all validation checks.[/]")
        return

    if not args.quiet:
        display_results(live_results)

    # ── Step 4: Save ─────────────────────────────────────────────────────
    output_file = args.output or os.path.join("output", f"{proto}_live.txt")
    save_results(live_results, output_file, args.json)
    console.print()


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list_sources:
        print_banner()
        list_sources()
        return

    print_banner()

    # Windows event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted. Exiting.[/]")
        sys.exit(0)


if __name__ == "__main__":
    main()
