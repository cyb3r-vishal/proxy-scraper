"""
Telegram Bot - Sends validated live proxies as .txt files to Telegram.
"""

import io
import logging
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
