# Snapshot refresh signals (`listen()`)

Frozen LOIP Events require the integration to GET `/api/v1/devices` immediately after:

1. the first WebSocket handshake succeeds
2. a drop, then a successful reconnect
3. an event frame that is not a JSON object

`listen_events()` still yields only `Event` (old `async for Event` consumers). Home Assistant and other LOIP consumers must use `listen()` so they do not wait for a 15s poll.

Do not read `aiolanbon` private attributes. Do not reimplement `/api/v1/events` in Home Assistant.

## Public types

```python
from aiolanbon import Event, SnapshotRefresh

SnapshotRefresh.CONNECTED      # first handshake
SnapshotRefresh.RECONNECTED    # handshake after a previous connection
SnapshotRefresh.PARSE_ERROR   # TEXT frame was not a JSON object
```

Each `SnapshotRefresh` means: clear ETag/If-None-Match cache, then GET `/devices` once.

## Minimal Home Assistant loop (phase 6)

```python
from aiolanbon import Event, LanbonClient, SnapshotRefresh

async def ha_events_loop(client: LanbonClient, coordinator) -> None:
    async for item in client.listen():
        if isinstance(item, SnapshotRefresh):
            coordinator.etag = None
            await coordinator.async_request_refresh()  # GET /api/v1/devices
            continue
        # item is Event
        if item.type == "state_changed":
            coordinator.apply_state_changed(item)  # memory only, no GET
            continue
        if item.needs_snapshot:
            coordinator.etag = None
            await coordinator.async_request_refresh()

# L8 (transports.events == "polling"): do not call listen(); keep GET /devices on the poll interval.
```

401 raises `LanbonAuthError` (no retry). 404/501 raise `LanbonEventsUnsupportedError` (fall back to polling). Cancelling the task raises `CancelledError`. Closing the generator (`break` / `aclose`) does not start another reconnect.
