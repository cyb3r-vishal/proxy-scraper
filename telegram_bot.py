"""
Telegram Bot - Sends validated live proxies as .txt files to Telegram.
Also supports forwarding daemon logs to Telegram.
"""

import asyncio
import io
import logging
import time
import httpx
from datetime import datetime

log = logging.getLogger("telegram")


class TelegramBot:
    """Sends proxy files to a Telegram chat via Bot API."""

    API = "https://api.telegram.org/bot{token}"

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base = self.API.format(token=token)

    async def send_message(self, text: str) -> bool:
        """Send a text message."""
        url = f"{self.base}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return True
                log.error("Telegram sendMessage failed: %s", resp.text)
                return False
        except Exception as e:
            log.error("Telegram sendMessage error: %s", e)
            return False

    async def send_file(
        self,
        proxies: list[str],
        proto: str,
        caption: str = "",
    ) -> bool:
        """Send proxies as a .txt file attachment."""
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"{proto}_live_{now}.txt"

        content = "\n".join(proxies)
        file_bytes = io.BytesIO(content.encode("utf-8"))
        file_bytes.name = filename

        url = f"{self.base}/sendDocument"

        if not caption:
            caption = (
                f"<b>{proto.upper()} Live Proxies</b>\n"
                f"Count: <b>{len(proxies)}</b>\n"
                f"Date: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                f"Validation: <b>3/3 endpoints passed</b>\n"
                f"Status: <b>100% Live</b>"
            )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    url,
                    data={
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={"document": (filename, file_bytes, "text/plain")},
                )
                if resp.status_code == 200:
                    log.info("Sent %d %s proxies to Telegram", len(proxies), proto)
                    return True
                log.error("Telegram sendDocument failed: %s", resp.text)
                return False
        except Exception as e:
            log.error("Telegram sendDocument error: %s", e)
            return False

    async def send_status(self, text: str) -> bool:
        """Send a status/notification message."""
        msg = f"🤖 <b>ProxyScraper Bot</b>\n\n{text}"
        return await self.send_message(msg)

    async def verify(self) -> bool:
        """Verify bot token is valid by calling getMe."""
        url = f"{self.base}/getMe"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    bot_name = data.get("result", {}).get("username", "unknown")
                    log.info("Telegram bot verified: @%s", bot_name)
                    return True
                log.error("Telegram bot verification failed: %s", resp.text)
                return False
        except Exception as e:
            log.error("Telegram bot verification error: %s", e)
            return False


# ---------------------------------------------------------------------------
#  Telegram Log Handler — forwards daemon logs to Telegram
# ---------------------------------------------------------------------------

class TelegramLogHandler(logging.Handler):
    """
    Logging handler that batches log lines and sends them to Telegram
    every `flush_interval` seconds to avoid API spam.
    """

    EMOJI_MAP = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔴",
    }

    def __init__(
        self,
        bot: "TelegramBot",
        loop: asyncio.AbstractEventLoop | None = None,
        flush_interval: float = 15.0,
        max_lines: int = 30,
    ):
        super().__init__(level=logging.INFO)
        self.bot = bot
        self._loop = loop
        self._buffer: list[str] = []
        self._lock = asyncio.Lock() if loop else None
        self._flush_interval = flush_interval
        self._max_lines = max_lines
        self._last_flush = time.monotonic()
        self._flush_task: asyncio.Task | None = None

    def emit(self, record: logging.LogRecord):
        """Buffer a log record and schedule a flush if needed."""
        # Skip logs from the telegram module itself to prevent recursion
        if record.name == "telegram":
            return

        emoji = self.EMOJI_MAP.get(record.levelname, "📝")
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        line = f"{emoji} <code>{ts}</code> {record.getMessage()}"
        self._buffer.append(line)

        # Flush if buffer is full or interval has passed
        now = time.monotonic()
        should_flush = (
            len(self._buffer) >= self._max_lines
            or now - self._last_flush >= self._flush_interval
        )

        if should_flush:
            self._schedule_flush()

    def _schedule_flush(self):
        """Schedule an async flush on the event loop."""
        loop = self._loop or asyncio.get_event_loop()
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = loop.create_task(self._async_flush())

    async def _async_flush(self):
        """Send buffered lines to Telegram."""
        if not self._buffer:
            return

        lines = self._buffer[: self._max_lines]
        self._buffer = self._buffer[self._max_lines :]
        self._last_flush = time.monotonic()

        text = (
            "📋 <b>Daemon Logs</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(lines)
        )

        # Telegram message limit is 4096 chars
        if len(text) > 4000:
            text = text[:4000] + "\n<i>... truncated</i>"

        try:
            await self.bot.send_message(text)
        except Exception:
            pass  # Don't let Telegram errors break logging

    async def flush_remaining(self):
        """Flush any remaining buffered logs (call before shutdown)."""
        while self._buffer:
            await self._async_flush()
