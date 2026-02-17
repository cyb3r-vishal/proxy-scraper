#!/usr/bin/env python3
"""
ProxyScraper Daemon — Runs 24/7, scrapes & validates proxies, sends to Telegram.

This script:
  1. Runs on a schedule (default: every 6 hours)
  2. Scrapes HTTP, HTTPS, SOCKS4, SOCKS5 proxies from 30+ sources
  3. Validates every proxy against multiple endpoints (must pass ALL)
  4. Collects until it has enough live proxies (target: 1000+)
  5. Sends each type as a .txt file to your Telegram bot
  6. Loops forever — designed to run as a systemd service on Linux VPS

Usage:
    python daemon.py                          # Run with .env config
    python daemon.py --interval 12            # Every 12 hours
    python daemon.py --types http socks5      # Only specific types
    python daemon.py --target 500             # Target 500 live proxies
    python daemon.py --once                   # Run once and exit
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Setup logging ────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "daemon.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("daemon")

# Suppress noisy httpx request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ── Imports ──────────────────────────────────────────────────────────────────

from scraper import scrape, SOURCES
from checker import check_all, ProxyResult, TIMEOUT_SECONDS
from telegram_bot import TelegramBot, TelegramLogHandler

# ── Constants ────────────────────────────────────────────────────────────────

ALL_TYPES = ["http", "https", "socks4", "socks5"]
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SHUTDOWN = asyncio.Event()


def load_env():
    """Load .env file if it exists (simple key=value parser)."""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key and value:
                    os.environ.setdefault(key, value)


def get_telegram_bot() -> TelegramBot | None:
    """Create TelegramBot from environment variables."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        return None
    return TelegramBot(token, chat_id)


# ── Core pipeline ───────────────────────────────────────────────────────────


async def scrape_and_validate(
    proto: str, target: int, timeout: int, bot: TelegramBot | None = None
) -> list[ProxyResult]:
    """Scrape and validate proxies for a single protocol type.

    Sends a .txt batch to Telegram every 10 live proxies found.
    """
    log.info("── [%s] Scraping from %d sources...", proto.upper(), len(SOURCES[proto]))

    # Cap raw proxies to avoid checking millions, but keep enough for target.
    # Live rate is typically 0.1-2%, so we need ~100× the target.
    max_raw = max(target * 100, 10_000)
    raw = await scrape(proto, max_proxies=max_raw)
    log.info("── [%s] Scraped %d raw proxies (cap: %d)", proto.upper(), len(raw), max_raw)

    if not raw:
        return []

    # Update timeout
    import checker
    checker.TIMEOUT_SECONDS = timeout

    log.info("── [%s] Validating %d proxies (target: %d live)...", proto.upper(), len(raw), target)

    checked = 0
    live_count = 0
    # Track unsent live proxies for batching every 10
    unsent_live: list[ProxyResult] = []
    batch_number = 0

    async def _send_live_batch(batch_proxies: list[ProxyResult], batch_num: int):
        """Send a batch of live proxies to Telegram as .txt."""
        if not bot or not batch_proxies:
            return
        proxy_list = [r.proxy for r in batch_proxies]
        avg_time = sum(r.response_time for r in batch_proxies) / len(batch_proxies)
        caption = (
            f"🔥 <b>{proto.upper()} Live Proxies — Batch #{batch_num}</b>\n\n"
            f"📊 Count: <b>{len(batch_proxies)}</b>\n"
            f"⚡ Avg Response: <b>{avg_time:.2f}s</b>\n"
            f"🔍 Validation: <b>3/3 endpoints passed</b>\n"
            f"📅 <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
            f"🟢 <b>100% Live & Verified</b>"
        )
        await bot.send_file(proxy_list, f"{proto}_batch{batch_num}", caption=caption)

    def on_progress(done: int, total: int, result: ProxyResult):
        nonlocal checked, live_count, unsent_live, batch_number
        checked = done
        if result.alive:
            live_count += 1
            unsent_live.append(result)

            # Send batch to Telegram every 10 live proxies
            if len(unsent_live) >= 10:
                batch_number += 1
                batch_to_send = unsent_live[:]
                unsent_live.clear()
                # Schedule send on event loop (non-blocking)
                asyncio.get_event_loop().create_task(
                    _send_live_batch(batch_to_send, batch_number)
                )

        # Log progress every 500 proxies
        if done % 500 == 0 or done == total:
            log.info(
                "── [%s] Progress: %d/%d checked, %d live",
                proto.upper(), done, total, live_count,
            )

    live = await check_all(raw, proto, on_progress=on_progress, target=target)

    # Send any remaining unsent live proxies (< 10)
    if unsent_live and bot:
        batch_number += 1
        await _send_live_batch(unsent_live, batch_number)
        unsent_live.clear()

    log.info(
        "── [%s] Validation complete: %d/%d live (%.1f%%)",
        proto.upper(), len(live), len(raw),
        (len(live) / len(raw) * 100) if raw else 0,
    )

    return live


async def save_proxies(results: list[ProxyResult], proto: str) -> Path:
    """Save live proxies to output file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filepath = OUTPUT_DIR / f"{proto}_live_{timestamp}.txt"

    with open(filepath, "w") as f:
        for r in results:
            f.write(r.proxy + "\n")

    # Also maintain a "latest" symlink/file
    latest = OUTPUT_DIR / f"{proto}_live_latest.txt"
    with open(latest, "w") as f:
        for r in results:
            f.write(r.proxy + "\n")

    log.info("── [%s] Saved %d proxies to %s", proto.upper(), len(results), filepath)
    return filepath


async def send_to_telegram(
    bot: TelegramBot, results: list[ProxyResult], proto: str
) -> bool:
    """Send validated proxies as .txt file to Telegram."""
    if not results:
        return False

    proxy_list = [r.proxy for r in results]

    # Build detailed caption
    avg_time = sum(r.response_time for r in results) / len(results)
    caption = (
        f"✅ <b>{proto.upper()} Live Proxies</b>\n\n"
        f"📊 Count: <b>{len(results)}</b>\n"
        f"⚡ Avg Response: <b>{avg_time:.2f}s</b>\n"
        f"🔍 Validation: <b>ALL endpoints passed</b>\n"
        f"📅 Date: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</code>\n"
        f"🟢 Status: <b>100% Live & Verified</b>"
    )

    return await bot.send_file(proxy_list, proto, caption=caption)


# ── Main loop ────────────────────────────────────────────────────────────────


async def run_cycle(
    types: list[str], target: int, timeout: int, bot: TelegramBot | None
):
    """Run one full scrape → validate → send cycle for all types."""
    cycle_start = time.monotonic()
    all_results: dict[str, list[ProxyResult]] = {}
    total_live = 0

    log.info("=" * 60)
    log.info("Starting new cycle at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("Types: %s | Target per type: %d | Timeout: %ds", ", ".join(types), target, timeout)
    log.info("=" * 60)

    if bot:
        await bot.send_status(
            f"🔄 <b>Starting proxy scan cycle</b>\n\n"
            f"Types: <code>{', '.join(t.upper() for t in types)}</code>\n"
            f"Target: <b>{target}</b> per type\n"
            f"Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )

    for proto in types:
        if SHUTDOWN.is_set():
            log.info("Shutdown requested, stopping cycle.")
            break

        try:
            live = await scrape_and_validate(proto, target, timeout, bot=bot)
            all_results[proto] = live

            if live:
                await save_proxies(live, proto)
                total_live += len(live)

                if bot:
                    await send_to_telegram(bot, live, proto)
            else:
                log.warning("── [%s] No live proxies found!", proto.upper())
                if bot:
                    await bot.send_status(
                        f"⚠️ <b>{proto.upper()}</b>: No live proxies found this cycle."
                    )

        except Exception as e:
            log.exception("── [%s] Error during cycle: %s", proto.upper(), e)
            if bot:
                await bot.send_status(
                    f"❌ <b>{proto.upper()}</b> error: <code>{str(e)[:200]}</code>"
                )

    elapsed = time.monotonic() - cycle_start

    summary = (
        f"📋 <b>Cycle Complete</b>\n\n"
        f"⏱ Duration: <b>{elapsed / 60:.1f} min</b>\n"
        f"🟢 Total Live: <b>{total_live}</b>\n"
    )
    for proto, results in all_results.items():
        summary += f"  • {proto.upper()}: <b>{len(results)}</b>\n"

    log.info("Cycle complete in %.1f min — %d total live proxies", elapsed / 60, total_live)

    if bot:
        await bot.send_status(summary)


async def daemon_loop(args):
    """Main daemon loop — runs cycles on interval."""
    load_env()

    bot = get_telegram_bot()
    tg_log_handler = None

    if bot:
        ok = await bot.verify()
        if ok:
            log.info("Telegram bot connected successfully")
            # Attach Telegram log handler — forward daemon logs to bot
            loop = asyncio.get_event_loop()
            tg_log_handler = TelegramLogHandler(bot, loop=loop, flush_interval=15.0)
            logging.getLogger("daemon").addHandler(tg_log_handler)
            log.info("Telegram log forwarding enabled")
        else:
            log.error("Telegram bot verification failed! Check your token.")
            bot = None
    else:
        log.warning(
            "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
        )

    types = args.types
    interval_hours = args.interval
    target = args.target
    timeout = args.timeout
    run_once = args.once

    # First run immediately
    await run_cycle(types, target, timeout, bot)

    if run_once:
        log.info("--once flag set. Exiting.")
        # Flush remaining logs to Telegram before exit
        if tg_log_handler:
            await tg_log_handler.flush_remaining()
        return

    # Then loop on schedule
    while not SHUTDOWN.is_set():
        next_run = datetime.now() + timedelta(hours=interval_hours)
        log.info("Next cycle at %s (in %d hours)", next_run.strftime("%H:%M:%S"), interval_hours)

        # Sleep in small increments so we can respond to shutdown
        sleep_seconds = interval_hours * 3600
        for _ in range(int(sleep_seconds / 10)):
            if SHUTDOWN.is_set():
                break
            await asyncio.sleep(10)

        if not SHUTDOWN.is_set():
            await run_cycle(types, target, timeout, bot)

    # Flush remaining logs on shutdown
    if tg_log_handler:
        await tg_log_handler.flush_remaining()


def handle_shutdown(signum, frame):
    """Handle SIGINT/SIGTERM gracefully."""
    log.info("Received signal %d, shutting down...", signum)
    SHUTDOWN.set()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proxy-daemon",
        description="24/7 Proxy Scraper Daemon — scrape, validate, send to Telegram",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=ALL_TYPES,
        default=ALL_TYPES,
        help="Proxy types to scrape (default: all)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=6,
        help="Hours between scan cycles (default: 6)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=1000,
        help="Target live proxies per type (default: 1000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=6,
        help="Timeout per proxy check in seconds (default: 6)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle and exit (for cron jobs)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    log.info("ProxyScraper Daemon starting...")
    log.info("PID: %d | Types: %s | Interval: %.1fh | Target: %d",
             os.getpid(), args.types, args.interval, args.target)

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        asyncio.run(daemon_loop(args))
    except KeyboardInterrupt:
        log.info("Interrupted. Exiting.")


if __name__ == "__main__":
    main()
