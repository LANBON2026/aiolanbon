from aiolanbon import LanbonAuthError, LanbonClient, LanbonRateLimitError
from aiolanbon.exceptions import LanbonApiError, LanbonTimeoutError
from tests.mock_loip import GATEWAY_ID, TOKEN, make_app
from aiohttp import ClientSession, ClientTimeout, web
import asyncio
import pytest


async def test_info_devices_command(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    info = await c.get_info()
    assert info.protocol == "loip"
    assert info.protocol_version == "1.0.0"
    assert info.api_enabled is True
    assert info.transports.events == "websocket"
    snap = await c.get_devices()
    assert snap is not None
    assert snap.revision == "1"
    caps = snap.capabilities()
    assert caps[0]["commands"] == ["set_on", "set_name"]
    assert caps[0]["features"] == ["on_off"]
    resp = await c.send_command(GATEWAY_ID, "switch:1", "set_on", {"on": True})
    assert resp.ok is True
    assert resp.status == "completed"
    assert resp.revision == "2"
    snap2 = await c.get_devices()
    assert snap2.devices[0].components[0].state["on"] is True
    same = await c.get_devices(if_none_match=snap2.revision)
    assert same is None


async def test_unauth_and_wrong_token(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], "", loip_server["session"])
    with pytest.raises(LanbonAuthError):
        await c.get_info()
    c2 = LanbonClient("127.0.0.1", loip_server["port"], "0" * 32, loip_server["session"])
    with pytest.raises(LanbonAuthError):
        await c2.get_devices()


async def test_rate_limit():
    app = make_app({"force_429": True})
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, TOKEN, session)
            with pytest.raises(LanbonRateLimitError) as ei:
                await c.send_command(GATEWAY_ID, "switch:1", "set_on", {"on": True})
            assert ei.value.retry_after == 1.0
    finally:
        await runner.cleanup()


async def test_device_offline_error():
    app = make_app({"offline": True})
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, TOKEN, session)
            with pytest.raises(LanbonApiError) as ei:
                await c.send_command(GATEWAY_ID, "switch:1", "set_on", {"on": True})
            assert ei.value.code == "device_offline"
    finally:
        await runner.cleanup()


async def test_timeout():
    app = make_app({"hang": True})
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession(timeout=ClientTimeout(total=1.0, sock_read=0.3)) as session:
            c = LanbonClient("127.0.0.1", port, TOKEN, session, timeout=0.3)
            with pytest.raises(LanbonTimeoutError):
                await asyncio.wait_for(c.get_info(), 2.0)
    finally:
        await asyncio.wait_for(runner.cleanup(), 2.0)
