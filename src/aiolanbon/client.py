"""LOIP 1.0.0 HTTP and WebSocket client.

Auth is Authorization: Bearer only. Token never goes in mDNS, URLs, logs, or exceptions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

import aiohttp

from ._redact import auth_headers
from .exceptions import (
    LanbonApiError,
    LanbonAuthError,
    LanbonConnectionError,
    LanbonEventsUnsupportedError,
    LanbonRateLimitError,
    LanbonTimeoutError,
)
from .models import CommandResponse, DeviceSnapshot, Event, GatewayInfo

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 8765
API_PREFIX = "/api/v1"
EVENTS_PATH = "/api/v1/events"
_JSON = "application/json; charset=utf-8"


class LanbonClient:
    """HTTP/WebSocket client for a LOIP gateway."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        session: aiohttp.ClientSession,
        *,
        scheme: str = "http",
        timeout: float = 8.0,
    ) -> None:
        self.host = host
        self.port = port or DEFAULT_PORT
        self._token = token
        self._session = session
        self.scheme = scheme if scheme in {"http", "https"} else "http"
        self._timeout = aiohttp.ClientTimeout(
            total=timeout, connect=timeout, sock_connect=timeout, sock_read=timeout
        )

    def __repr__(self) -> str:
        return f"LanbonClient(host={self.host!r}, port={self.port}, scheme={self.scheme!r})"

    @property
    def base(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"

    @property
    def events_url(self) -> str:
        ws_scheme = "wss" if self.scheme == "https" else "ws"
        return f"{ws_scheme}://{self.host}:{self.port}{EVENTS_PATH}"

    def _headers(self) -> dict[str, str]:
        return auth_headers(self._token)

    async def get_info(self) -> GatewayInfo:
        data = await self._request("GET", f"{API_PREFIX}/info")
        return GatewayInfo.from_dict(data)

    async def get_devices(self, if_none_match: str | None = None) -> DeviceSnapshot | None:
        headers = {}
        if if_none_match:
            etag = if_none_match if if_none_match.startswith('"') else f'"{if_none_match}"'
            headers["If-None-Match"] = etag
        data = await self._request("GET", f"{API_PREFIX}/devices", extra_headers=headers, allow_304=True)
        if data is None:
            return None
        return DeviceSnapshot.from_dict(data)

    async def command(self, payload: dict[str, Any]) -> CommandResponse:
        body = dict(payload)
        body.setdefault("request_id", uuid.uuid4().hex[:16])
        body.setdefault("params", {})
        data = await self._request("POST", f"{API_PREFIX}/command", json_body=body)
        resp = CommandResponse.from_dict(data)
        if resp.ok:
            return resp
        raise LanbonApiError(
            resp.error_code or "internal_error",
            resp.error_message or "",
            details=resp.error_details,
            request_id=resp.request_id or None,
        )

    async def send_command(
        self,
        device_id: str,
        component_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> CommandResponse:
        return await self.command(
            {
                "request_id": request_id or uuid.uuid4().hex[:16],
                "device_id": device_id,
                "component_id": component_id,
                "command": command,
                "params": params or {},
            }
        )

    async def listen_events(self) -> AsyncIterator[Event]:
        """Yield LOIP events from `/api/v1/events`. Reconnects with bounded backoff.

        Does not put the token in the URL. 401 is not retried. 404/501 raises
        LanbonEventsUnsupportedError so the caller can poll `/devices`.
        """
        delay = 1.0
        while True:
            try:
                ws_kwargs: dict[str, Any] = {
                    "headers": self._headers(),
                    "heartbeat": 30,
                }
                try:
                    from aiohttp import ClientWSTimeout

                    ws_kwargs["timeout"] = ClientWSTimeout(ws_close=10.0)
                except Exception:
                    pass
                async with self._session.ws_connect(self.events_url, **ws_kwargs) as ws:
                    delay = 1.0
                    _LOGGER.debug("LOIP WS connected %s:%s", self.host, self.port)
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except json.JSONDecodeError:
                                continue
                            if not isinstance(data, dict):
                                continue
                            yield Event.from_dict(data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                raise
            except aiohttp.WSServerHandshakeError as err:
                status = getattr(err, "status", None)
                if status == 401:
                    raise LanbonAuthError("unauthorized") from None
                if status in {404, 501}:
                    raise LanbonEventsUnsupportedError("events websocket not available") from None
                _LOGGER.debug("LOIP WS handshake failed status=%s", status)
            except TimeoutError:
                _LOGGER.debug("LOIP WS timeout")
            except aiohttp.ClientError as err:
                _LOGGER.debug("LOIP WS transport %s", type(err).__name__)
            jitter = random.uniform(0, min(0.5, delay * 0.1))
            await asyncio.sleep(delay + jitter)
            delay = min(60.0, delay * 2)

    async def ws_listen(self, on_message: Callable[[dict[str, Any]], None]) -> None:
        """Compatibility wrapper: dict callback instead of Event objects."""
        async for event in self.listen_events():
            on_message(
                {
                    "protocol_version": event.protocol_version,
                    "event_id": event.event_id,
                    "revision": event.revision,
                    "type": event.type,
                    "device_id": event.device_id,
                    "component_id": event.component_id,
                    "state": event.state,
                    "online": event.online,
                    "action": event.action,
                    "request_id": event.request_id,
                    "status": event.status,
                    "error": event.error,
                    "timestamp": event.timestamp,
                }
            )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        allow_304: bool = False,
    ) -> dict[str, Any] | None:
        headers = {**self._headers()}
        if extra_headers:
            headers.update(extra_headers)
        url = f"{self.base}{path}"
        try:
            kwargs: dict[str, Any] = {
                "headers": headers,
                "timeout": self._timeout,
            }
            if json_body is not None:
                kwargs["data"] = json.dumps(json_body)
                headers["Content-Type"] = _JSON
            async with self._session.request(method, url, **kwargs) as resp:
                return await self._handle_response(resp, allow_304=allow_304)
        except (TimeoutError, aiohttp.ServerTimeoutError) as err:
            raise LanbonTimeoutError("timeout") from err
        except aiohttp.ClientError as err:
            if type(err).__name__.endswith("TimeoutError"):
                raise LanbonTimeoutError("timeout") from err
            raise LanbonConnectionError(type(err).__name__) from err

    async def _handle_response(
        self, resp: aiohttp.ClientResponse, *, allow_304: bool
    ) -> dict[str, Any] | None:
        if resp.status == 304 and allow_304:
            return None
        if resp.status == 401:
            raise LanbonAuthError("unauthorized")
        if resp.status == 429:
            retry = resp.headers.get("Retry-After")
            retry_after = None
            if retry:
                try:
                    retry_after = float(retry)
                except ValueError:
                    retry_after = None
            raise LanbonRateLimitError("rate_limited", retry_after=retry_after)

        raw = await resp.read()
        data: Any = {}
        if raw:
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as err:
                raise LanbonConnectionError("invalid JSON object response") from err

        if isinstance(data, dict) and data.get("ok") is False:
            err = data.get("error") if isinstance(data.get("error"), dict) else {}
            code = str(err.get("code") or "internal_error")
            raise LanbonApiError(
                code,
                str(err.get("message") or ""),
                details=dict(err.get("details") or {}),
                request_id=str(data["request_id"]) if data.get("request_id") else None,
                http_status=resp.status,
            )

        if resp.status >= 400:
            raise LanbonApiError(
                _code_for_status(resp.status),
                "",
                http_status=resp.status,
            )
        if not isinstance(data, dict):
            raise LanbonConnectionError("invalid JSON object response")
        return data


def _code_for_status(status: int) -> str:
    return {
        400: "invalid_request",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        500: "internal_error",
        503: "device_offline",
        504: "timeout",
    }.get(status, "internal_error")
