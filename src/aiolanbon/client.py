"""HTTP/WebSocket client for LANBON Mesh root local API."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .exceptions import (
    LanbonAuthError,
    LanbonCommandError,
    LanbonConnectionError,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=8)
DEFAULT_PORT = 8765


class LanbonClient:
    """HTTP/WebSocket client for the LANBON Mesh root local API."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.port = port or DEFAULT_PORT
        self.token = token
        self._session = session

    @property
    def base(self) -> str:
        """Return the HTTP base URL."""
        return f"http://{self.host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def get_info(self) -> dict[str, Any]:
        """Fetch host info from GET /api/v1/info."""
        return await self._get("/api/v1/info")

    async def get_devices(self) -> dict[str, Any]:
        """Fetch host and child snapshot from GET /api/v1/devices."""
        return await self._get("/api/v1/devices")

    async def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a command via POST /api/v1/command."""
        try:
            async with self._session.post(
                f"{self.base}/api/v1/command",
                headers={**self._headers(), "Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    raise LanbonAuthError("invalid token")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise LanbonConnectionError(str(err)) from err

        if isinstance(data, dict) and data.get("ok") is False:
            raise LanbonCommandError(str(data.get("err") or "command failed"))
        if not isinstance(data, dict):
            raise LanbonConnectionError("invalid command response")
        return data

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{self.base}{path}", headers=self._headers(), timeout=_TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise LanbonAuthError("invalid token")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise LanbonConnectionError(str(err)) from err
        if not isinstance(data, dict):
            raise LanbonConnectionError("invalid JSON object response")
        return data

    async def ws_listen(self, on_message: Callable[[dict[str, Any]], None]) -> None:
        """Listen for WebSocket pushes until cancelled.

        Does not log the authenticated URL (token is in the query string).
        """
        url = f"ws://{self.host}:{self.port}/api/v1/ws?token={self.token}"
        while True:
            try:
                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    _LOGGER.debug("LANBON WS connected %s:%s", self.host, self.port)
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except json.JSONDecodeError:
                                continue
                            if isinstance(data, dict):
                                on_message(data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                # Avoid logging err verbatim — handshake errors can embed the URL/token.
                _LOGGER.debug("LANBON WS reconnecting after error: %s", type(err).__name__)
            await asyncio.sleep(5)
