"""URL construction for IPv4, DNS names, and IPv6 literals.

Loopback ::1 checks aiohttp can open the built URL. No IPv6 LAN panel was used.
"""

from __future__ import annotations

import os

from aiohttp import ClientSession, web
import pytest
from yarl import URL

from aiolanbon import LanbonClient
from tests.mock_loip import TOKEN, make_app


class _Sess:
    pass


def _client(host: str, port: int = 8765, scheme: str = "http") -> LanbonClient:
    return LanbonClient(host, port, TOKEN, _Sess(), scheme=scheme)  # type: ignore[arg-type]


def test_ipv4_http_ws_keeps_port():
    c = _client("192.168.0.155", 8765)
    assert c.base == "http://192.168.0.155:8765"
    assert c.events_url == "ws://192.168.0.155:8765/api/v1/events"
    assert TOKEN not in c.base
    assert TOKEN not in c.events_url
    assert "token=" not in c.events_url


def test_dns_https_wss_custom_port():
    c = _client("panel.local", 8443, scheme="https")
    assert c.base == "https://panel.local:8443"
    assert c.events_url == "wss://panel.local:8443/api/v1/events"


def test_ipv6_literal_is_bracketed_once():
    c = _client("2001:db8::1", 8765)
    assert c.base == "http://[2001:db8::1]:8765"
    assert c.events_url == "ws://[2001:db8::1]:8765/api/v1/events"
    assert c.base.count("[") == 1
    assert c.base.count("]") == 1
    parsed = URL(c.base)
    assert parsed.host == "2001:db8::1"
    assert parsed.port == 8765


def test_ipv6_already_bracketed_is_not_doubled():
    c = _client("[2001:db8::1]", 8765)
    assert c.base == "http://[2001:db8::1]:8765"
    assert c.events_url == "ws://[2001:db8::1]:8765/api/v1/events"
    assert "[[" not in c.base
    assert "]]" not in c.base


def test_ipv6_https_wss():
    c = _client("2001:db8::1", 443, scheme="https")
    assert c.base == "https://[2001:db8::1]"
    assert c.events_url == "wss://[2001:db8::1]/api/v1/events"
    assert URL(c.events_url).port == 443


def test_loopback_ipv6_literal():
    c = _client("::1", 8765)
    assert c.base == "http://[::1]:8765"
    assert c.events_url == "ws://[::1]:8765/api/v1/events"


async def test_ipv6_loopback_http_and_ws_transport():
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "::1", 0)
    try:
        await site.start()
    except OSError as err:
        await runner.cleanup()
        if os.environ.get("REQUIRE_IPV6") == "1":
            raise
        pytest.skip(f"IPv6 loopback not available: {err}")
    port = int(site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession() as session:
            c = LanbonClient("::1", port, TOKEN, session)
            assert c.base == f"http://[::1]:{port}"
            info = await c.get_info()
            assert info.protocol == "loip"
            event = None
            async for ev in c.listen_events():
                event = ev
                break
            assert event is not None
            assert event.type == "state_changed"
    finally:
        await runner.cleanup()
