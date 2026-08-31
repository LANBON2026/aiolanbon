# LOIP 1.0.0 field coverage

Protocol: `lanbon/loip-protocol` `v1.0.0-internal.1` / `c24f7cdacfee9e2e89d57ce40c84b5c242013680`.  
Library maps JSON; it does not invent fields.

| Area | Protocol | Client |
|---|---|---|
| info | GET `/api/v1/info` | `get_info()` → `GatewayInfo` |
| devices | GET `/api/v1/devices` + `revision` + ETag/304 | `get_devices(if_none_match=)` |
| components | `devices[].components[]` | `Device.components` / `Device.component()` |
| capabilities | `features`, `commands`, `constraints`, `type`, `enabled` | `Component.capabilities` / `DeviceSnapshot.capabilities()` |
| command | POST `/api/v1/command` | `command()` / `send_command()` |
| events | GET `/api/v1/events` WS, Bearer header | `listen()` (`SnapshotRefresh` + `Event`); `listen_events()` / `ws_listen()` stay Event-only |
| revision | opaque string; resync via `/devices` | compared for equality only; `Event.needs_snapshot` |
| error | `ok` + `error.code` + HTTP 401/429/4xx/5xx | `LanbonAuthError`, `LanbonRateLimitError`, `LanbonTimeoutError`, `LanbonApiError.code` |
| mDNS | `_lanbon._tcp`, no token in TXT | `parse_mdns_txt` / `discovered_from_mdns` |
| auth | Bearer header, not URL/query | `events_url` has no query; `__repr__` has no token |

`series` and `model` are stored for display. Command and entity decisions must use capabilities, not series names.
