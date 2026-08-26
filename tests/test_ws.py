import asyncio

import pytest
from aiohttp import ClientSession, web

from aiolanbon import LanbonAuthError, LanbonClient, LanbonEventsUnsupportedError
from tests.mock_loip import TOKEN, make_app


async def test_ws_event_and_no_token_in_url(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    assert "token=" not in c.events_url
    assert TOKEN not in c.events_url
    assert c.events_url.endswith("/api/v1/events")
    event = None
    async for ev in c.listen_events():
        event = ev
        break
    assert event is not None
    assert event.type == "state_changed"
    assert event.component_id == "switch:1"
    assert event.state == {"on": True}
    assert event.revision == "2"


async def test_ws_reconnect(loip_server):
    loip_server["app"]["st"]["ws_close_first"] = True
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])

    async def _fast_sleep(_delay):
        return None

    asyncio_sleep = asyncio.sleep

    async def _sleep(delay):
        if delay > 0.05:
            return None
        await asyncio_sleep(delay)

    # bounded backoff still calls sleep; skip the wait
    monkey_sleep = pytest.MonkeyPatch()
    monkey_sleep.setattr(asyncio, "sleep", _sleep)
    try:
        event = None
        async for ev in c.listen_events():
            event = ev
            break
        assert event is not None
        assert loip_server["app"]["st"]["ws_connections"] >= 2
    finally:
        monkey_sleep.undo()


async def test_ws_unauthorized():
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, "0" * 32, session)
            with pytest.raises(LanbonAuthError):
                async for _ in c.listen_events():
                    break
    finally:
        await runner.cleanup()


async def test_ws_unsupported():
    app = web.Application()

    async def missing(_request):
        raise web.HTTPNotFound()

    app.router.add_get("/api/v1/events", missing)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, TOKEN, session)
            with pytest.raises(LanbonEventsUnsupportedError):
                async for _ in c.listen_events():
                    break
    finally:
        await runner.cleanup()
