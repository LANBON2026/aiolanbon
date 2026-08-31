"""Async LOIP 1.0.0 client. No Home Assistant dependency. No series branching."""

from .client import LanbonClient
from .discovery import (
    MDNS_SERVICE_TYPE,
    discover,
    discovered_from_mdns,
    parse_mdns_txt,
)
from .exceptions import (
    LanbonApiError,
    LanbonAuthError,
    LanbonCommandError,
    LanbonConnectionError,
    LanbonError,
    LanbonEventsUnsupportedError,
    LanbonRateLimitError,
    LanbonTimeoutError,
)
from .models import (
    CommandResponse,
    Component,
    Device,
    DeviceSnapshot,
    DiscoveredGateway,
    Event,
    GatewayInfo,
    SnapshotRefresh,
)

__all__ = [
    "CommandResponse",
    "Component",
    "Device",
    "DeviceSnapshot",
    "DiscoveredGateway",
    "Event",
    "GatewayInfo",
    "SnapshotRefresh",
    "LanbonApiError",
    "LanbonAuthError",
    "LanbonClient",
    "LanbonCommandError",
    "LanbonConnectionError",
    "LanbonError",
    "LanbonEventsUnsupportedError",
    "LanbonRateLimitError",
    "LanbonTimeoutError",
    "MDNS_SERVICE_TYPE",
    "discover",
    "discovered_from_mdns",
    "parse_mdns_txt",
]

__version__ = "0.2.0"

LoipClient = LanbonClient
