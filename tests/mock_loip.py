"""In-process LOIP 1.0.0 mock for unit tests."""

from __future__ import annotations

import json
from typing import Any

import asyncio

from aiohttp import WSMsgType, web

TOKEN = "a" * 32
GATEWAY_ID = "aabbccddeeff"

INFO = {
    "protocol": "loip",
    "protocol_version": "1.0.0",
    "gateway_id": GATEWAY_ID,
    "manufacturer": "LANBON",
    "series": "L10",
    "model": "L10",
    "firmware_version": "1.1.28",
    "hardware_version": "esp32s3",
    "api_enabled": True,
    "transports": {"http": True, "events": "websocket"},
    "limits": {
        "max_command_body_bytes": 1024,
        "max_devices": 64,
        "max_components_per_device": 8,
        "offline_retention_seconds": 249,
    },
}

SNAPSHOT = {
    "protocol_version": "1.0.0",
    "gateway_id": GATEWAY_ID,
    "revision": "1",
    "devices": [
        {
            "id": GATEWAY_ID,
            "name": "Root",
            "manufacturer": "LANBON",
            "series": "L10",
            "model": "L10-1G",
            "online": True,
            "role": "gateway",
            "components": [
                {
                    "id": "switch:1",
                    "type": "switch",
                    "name": "Light1",
                    "enabled": True,
                    "features": ["on_off"],
                    "commands": ["set_on", "set_name"],
                    "state": {"on": False},
                    "constraints": {"name": {"max_bytes": 39}},
                }
            ],
        }
    ],
}


def _bearer_ok(request: web.Request) -> bool:
    header = request.headers.get("Authorization", "")
    return header == f"Bearer {TOKEN}"


def _unauthorized() -> web.Response:
    return web.json_response(
        {
            "ok": False,
            "error": {
                "code": "unauthorized",
                "message": "Missing or invalid bearer token",
                "details": {},
            },
        },
        status=401,
    )


def make_app(state: dict[str, Any] | None = None) -> web.Application:
    st: dict[str, Any] = {
        "snapshot": json.loads(json.dumps(SNAPSHOT)),
        "ws_connections": 0,
        "ws_close_first": False,
        "hang": False,
        "force_429": False,
        "events": [
            {
                "protocol_version": "1.0.0",
                "event_id": "e1",
                "revision": "2",
                "type": "state_changed",
                "device_id": GATEWAY_ID,
                "component_id": "switch:1",
                "state": {"on": True},
            }
        ],
    }
    if state:
        st.update(state)
    app = web.Application()
    app["st"] = st

    async def info(request: web.Request) -> web.Response:
        if not _bearer_ok(request):
            return _unauthorized()
        return web.json_response(INFO)

    async def devices(request: web.Request) -> web.Response:
        if not _bearer_ok(request):
            return _unauthorized()
        snap = app["st"]["snapshot"]
        rev = snap["revision"]
        inm = request.headers.get("If-None-Match", "").strip('"')
        if inm and inm == rev:
            return web.Response(status=304)
        return web.json_response(snap, headers={"ETag": f'"{rev}"'})

    async def command(request: web.Request) -> web.Response:
        if not _bearer_ok(request):
            return _unauthorized()
        if app["st"].get("force_429"):
            return web.json_response(
                {
                    "ok": False,
                    "error": {"code": "rate_limited", "message": "slow down", "details": {}},
                },
                status=429,
                headers={"Retry-After": "1"},
            )
        body = await request.json()
        if app["st"].get("offline"):
            return web.json_response(
                {
                    "request_id": body.get("request_id"),
                    "ok": False,
                    "error": {
                        "code": "device_offline",
                        "message": "offline",
                        "details": {},
                    },
                },
                status=503,
            )
        snap = app["st"]["snapshot"]
        rev = str(int(snap["revision"]) + 1)
        snap["revision"] = rev
        on = bool((body.get("params") or {}).get("on", True))
        snap["devices"][0]["components"][0]["state"]["on"] = on
        return web.json_response(
            {
                "request_id": body.get("request_id"),
                "ok": True,
                "status": "completed",
                "revision": rev,
            }
        )

    async def events(request: web.Request) -> web.WebSocketResponse:
        if not _bearer_ok(request):
            raise web.HTTPUnauthorized()
        if "token" in str(request.rel_url):
            raise web.HTTPBadRequest(text="token must not be in the URL")
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        app["st"]["ws_connections"] += 1
        if app["st"].get("ws_close_first") and app["st"]["ws_connections"] == 1:
            await ws.close()
            return ws
        for ev in app["st"]["events"]:
            await ws.send_json(ev)
        async for msg in ws:
            if msg.type in {WSMsgType.CLOSE, WSMsgType.ERROR}:
                break
        return ws

    async def hang(request: web.Request) -> web.Response:
        if not _bearer_ok(request):
            return _unauthorized()
        await asyncio.sleep(1.0)
        return web.json_response(INFO)

    app.router.add_get("/api/v1/info", hang if st.get("hang") else info)
    app.router.add_get("/api/v1/devices", devices)
    app.router.add_post("/api/v1/command", command)
    app.router.add_get("/api/v1/events", events)
    return app
