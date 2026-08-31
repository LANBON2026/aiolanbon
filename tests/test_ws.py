import asyncio

import pytest
from aiohttp import ClientSession, web

from aiolanbon import (
    Event,
    LanbonAuthError,
    LanbonClient,
    LanbonEventsUnsupportedError,
    SnapshotRefresh,
)
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


def _skip_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio_sleep = asyncio.sleep

    async def _sleep(delay):
        if delay > 0.05:
            return None
        await asyncio_sleep(delay)

    monkeypatch.setattr(asyncio, "sleep", _sleep)


async def _serve(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    return runner, port


async def test_listen_first_connect_signals_refresh(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    items = []
    async for item in c.listen():
        items.append(item)
        if isinstance(item, Event):
            break
    assert isinstance(items[0], SnapshotRefresh)
    assert items[0].reason == SnapshotRefresh.CONNECTED
    assert items[0].needs_snapshot is True
    assert isinstance(items[1], Event)
    assert items[1].type == "state_changed"


async def test_listen_reconnect_signals_reconnected(loip_server, monkeypatch):
    loip_server["app"]["st"]["ws_close_first"] = True
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    _skip_backoff(monkeypatch)
    reasons = []
    event = None
    async for item in c.listen():
        if isinstance(item, SnapshotRefresh):
            reasons.append(item.reason)
            continue
        event = item
        break
    assert reasons == [SnapshotRefresh.CONNECTED, SnapshotRefresh.RECONNECTED]
    assert isinstance(event, Event)
    assert loip_server["app"]["st"]["ws_connections"] >= 2


async def test_listen_malformed_json_signals_parse_error(loip_server):
    good = loip_server["app"]["st"]["events"][0]
    loip_server["app"]["st"]["events"] = ["{", "not-json", "[]", good]
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    items = []
    async for item in c.listen():
        items.append(item)
        if isinstance(item, Event):
            break
    assert items[0].reason == SnapshotRefresh.CONNECTED
    assert [i.reason for i in items[1:4]] == [SnapshotRefresh.PARSE_ERROR] * 3
    assert isinstance(items[4], Event)
    assert items[4].event_id == "e1"


async def test_listen_events_skips_refresh_old_consumer(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    event = None
    async for ev in c.listen_events():
        event = ev
        break
    assert type(event) is Event
    assert event.type == "state_changed"


async def test_ws_listen_callback_still_event_dict(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    got = []

    async def _run():
        await c.ws_listen(lambda d: got.append(d))

    task = asyncio.create_task(_run())
    try:
        for _ in range(50):
            if got:
                break
            await asyncio.sleep(0.02)
        assert got
        assert got[0]["type"] == "state_changed"
        assert got[0]["component_id"] == "switch:1"
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_listen_unauthorized():
    runner, port = await _serve(make_app())
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, "0" * 32, session)
            with pytest.raises(LanbonAuthError):
                async for _ in c.listen():
                    break
    finally:
        await runner.cleanup()


@pytest.mark.parametrize("exc", [web.HTTPNotFound, web.HTTPNotImplemented])
async def test_listen_unsupported(exc):
    app = web.Application()

    async def missing(_request):
        raise exc()

    app.router.add_get("/api/v1/events", missing)
    runner, port = await _serve(app)
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, TOKEN, session)
            with pytest.raises(LanbonEventsUnsupportedError):
                async for _ in c.listen():
                    break
    finally:
        await runner.cleanup()


async def test_ws_unsupported_501():
    app = web.Application()

    async def missing(_request):
        raise web.HTTPNotImplemented()

    app.router.add_get("/api/v1/events", missing)
    runner, port = await _serve(app)
    try:
        async with ClientSession() as session:
            c = LanbonClient("127.0.0.1", port, TOKEN, session)
            with pytest.raises(LanbonEventsUnsupportedError):
                async for _ in c.listen_events():
                    break
    finally:
        await runner.cleanup()


async def test_listen_cancelled(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])

    async def _run():
        async for _ in c.listen():
            await asyncio.sleep(3600)

    task = asyncio.create_task(_run())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_listen_aclose_does_not_reconnect(loip_server):
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN, loip_server["session"])
    agen = c.listen()
    first = await agen.__anext__()
    assert isinstance(first, SnapshotRefresh)
    assert first.reason == SnapshotRefresh.CONNECTED
    n = loip_server["app"]["st"]["ws_connections"]
    await agen.aclose()
    await asyncio.sleep(0.2)
    assert loip_server["app"]["st"]["ws_connections"] == n
