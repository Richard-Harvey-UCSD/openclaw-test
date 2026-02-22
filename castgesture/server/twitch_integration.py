"""Twitch chat bot and channel point integration for CastGesture."""

import asyncio
import re
from typing import Callable, Optional


class TwitchBot:
    def __init__(self, channel: str, oauth_token: str, bot_name: str = "CastGestureBot"):
        self.channel = channel.lstrip("#")
        self.oauth_token = oauth_token
        self.bot_name = bot_name
        self._reader = None
        self._writer = None
        self._running = False
        self._on_command: Optional[Callable] = None
        self._on_redeem: Optional[Callable] = None

    def on_command(self, callback: Callable):
        self._on_command = callback

    def on_redeem(self, callback: Callable):
        self._on_redeem = callback

    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection("irc.chat.twitch.tv", 6667)
        self._writer.write(f"PASS {self.oauth_token}\r\n".encode())
        self._writer.write(f"NICK {self.bot_name}\r\n".encode())
        self._writer.write(f"JOIN #{self.channel}\r\n".encode())
        self._writer.write(b"CAP REQ :twitch.tv/commands twitch.tv/tags\r\n")
        await self._writer.drain()
        self._running = True

    async def disconnect(self):
        self._running = False
        if self._writer:
            self._writer.close()

    async def send_message(self, message: str):
        if self._writer:
            self._writer.write(f"PRIVMSG #{self.channel} :{message}\r\n".encode())
            await self._writer.drain()

    async def run(self):
        await self.connect()
        while self._running:
            try:
                line = await asyncio.wait_for(self._reader.readline(), timeout=30)
                decoded = line.decode("utf-8", errors="ignore").strip()
                if not decoded:
                    continue
                if decoded.startswith("PING"):
                    self._writer.write(f"PONG {decoded[5:]}\r\n".encode())
                    await self._writer.drain()
                    continue
                await self._handle_message(decoded)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def _handle_message(self, raw: str):
        # Parse PRIVMSG
        match = re.search(r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)", raw)
        if match:
            user = match.group(1)
            message = match.group(2).strip()

            # Check for !gesture commands
            if message.startswith("!gesture ") and self._on_command:
                cmd = message[9:].strip()
                await self._on_command(user, cmd)
            elif message.startswith("!effect ") and self._on_command:
                cmd = message[8:].strip()
                await self._on_command(user, cmd)

        # Check for channel point redemptions (custom-reward-id in tags)
        if "custom-reward-id=" in raw and self._on_redeem:
            reward_match = re.search(r"custom-reward-id=([a-f0-9-]+)", raw)
            user_match = re.search(r":(\w+)!\w+@", raw)
            if reward_match and user_match:
                await self._on_redeem(user_match.group(1), reward_match.group(1))
