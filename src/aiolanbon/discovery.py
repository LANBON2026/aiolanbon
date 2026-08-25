"""mDNS TXT parsing for `_lanbon._tcp`. Token is never read or stored."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._redact import ALLOWED_MDNS_TXT, FORBIDDEN_SECRET_KEYS
from .models import DiscoveredGateway

MDNS_SERVICE_TYPE = "_lanbon._tcp.local."


def _norm_key(key: Any) -> str:
    if isinstance(key, bytes):
        key = key.decode("utf-8", "replace")
    return str(key).strip().lower()


def _norm_val(val: Any) -> str:
    if isinstance(val, bytes):
        val = val.decode("utf-8", "replace")
    return str(val)


def parse_mdns_txt(properties: Mapping[Any, Any] | None) -> dict[str, str]:
    """Return only the LOIP-allowed TXT fields. Secret keys are dropped."""
    out: dict[str, str] = {}
    for key, val in (properties or {}).items():
        name = _norm_key(key)
        if name in FORBIDDEN_SECRET_KEYS:
            continue
        if name not in ALLOWED_MDNS_TXT:
            continue
        out[name] = _norm_val(val)
    return out


def discovered_from_mdns(
    host: str,
    port: int,
    properties: Mapping[Any, Any] | None,
) -> DiscoveredGateway:
    txt = parse_mdns_txt(properties)
    scheme = txt.get("scheme") or "http"
    if scheme not in {"http", "https"}:
        scheme = "http"
    return DiscoveredGateway(
        host=host,
        port=int(port or 8765),
        gateway_id=txt.get("id") or "",
        api=txt.get("api") or "1",
        path=txt.get("path") or "/api/v1",
        series=txt.get("series") or "",
        model=txt.get("model") or "",
        auth=txt.get("auth") or "bearer",
        scheme=scheme,
    )


async def discover(timeout: float = 3.0) -> list[DiscoveredGateway]:
    """Browse `_lanbon._tcp.local.` if zeroconf is installed."""
    try:
        from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
        from zeroconf.asyncio import AsyncZeroconf
    except ImportError as err:
        raise RuntimeError("zeroconf is required for mDNS discover()") from err

    import asyncio

    found: dict[tuple[str, int], DiscoveredGateway] = {}
    aiozc = AsyncZeroconf()

    def _on_change(
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        if state_change is ServiceStateChange.Removed:
            return
        info = zeroconf.get_service_info(service_type, name)
        if info is None:
            return
        parsed = info.parsed_addresses()
        host = parsed[0] if parsed else ""
        if not host:
            return
        item = discovered_from_mdns(host, info.port or 8765, info.properties)
        found[(item.host, item.port)] = item

    browser = ServiceBrowser(aiozc.zeroconf, MDNS_SERVICE_TYPE, handlers=[_on_change])
    try:
        await asyncio.sleep(timeout)
    finally:
        browser.cancel()
        await aiozc.async_close()
    return list(found.values())
