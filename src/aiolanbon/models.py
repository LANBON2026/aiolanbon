"""LOIP 1.0.0 data models. Unknown JSON fields are kept in `extra` and ignored by logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal


def _extra(data: dict[str, Any], known: set[str]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k not in known}


@dataclass(frozen=True)
class Transports:
    http: bool = True
    events: str = "polling"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Transports:
        data = data or {}
        return cls(
            http=bool(data.get("http", True)),
            events=str(data.get("events") or "polling"),
            extra=_extra(data, {"http", "events"}),
        )


@dataclass(frozen=True)
class Limits:
    max_command_body_bytes: int = 1024
    max_devices: int = 1
    max_components_per_device: int = 1
    offline_retention_seconds: int = 1
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Limits:
        data = data or {}
        return cls(
            max_command_body_bytes=int(data.get("max_command_body_bytes") or 1024),
            max_devices=int(data.get("max_devices") or 1),
            max_components_per_device=int(data.get("max_components_per_device") or 1),
            offline_retention_seconds=int(data.get("offline_retention_seconds") or 1),
            extra=_extra(
                data,
                {
                    "max_command_body_bytes",
                    "max_devices",
                    "max_components_per_device",
                    "offline_retention_seconds",
                },
            ),
        )


@dataclass(frozen=True)
class GatewayInfo:
    protocol: str
    protocol_version: str
    gateway_id: str
    manufacturer: str
    series: str
    model: str
    firmware_version: str
    api_enabled: bool
    transports: Transports
    limits: Limits
    hardware_version: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def events_websocket(self) -> bool:
        return self.transports.events == "websocket"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GatewayInfo:
        return cls(
            protocol=str(data.get("protocol") or ""),
            protocol_version=str(data.get("protocol_version") or ""),
            gateway_id=str(data.get("gateway_id") or ""),
            manufacturer=str(data.get("manufacturer") or ""),
            series=str(data.get("series") or ""),
            model=str(data.get("model") or ""),
            firmware_version=str(data.get("firmware_version") or ""),
            api_enabled=bool(data.get("api_enabled")),
            transports=Transports.from_dict(data.get("transports") if isinstance(data.get("transports"), dict) else {}),
            limits=Limits.from_dict(data.get("limits") if isinstance(data.get("limits"), dict) else {}),
            hardware_version=str(data["hardware_version"]) if data.get("hardware_version") is not None else None,
            extra=_extra(
                data,
                {
                    "protocol",
                    "protocol_version",
                    "gateway_id",
                    "manufacturer",
                    "series",
                    "model",
                    "firmware_version",
                    "hardware_version",
                    "api_enabled",
                    "transports",
                    "limits",
                },
            ),
        )


@dataclass(frozen=True)
class Component:
    id: str
    type: str
    name: str
    enabled: bool
    features: tuple[str, ...]
    commands: tuple[str, ...]
    state: dict[str, Any]
    constraints: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def capabilities(self) -> dict[str, Any]:
        """Declared abilities. Callers must not substitute series/model for this."""
        return {
            "id": self.id,
            "type": self.type,
            "enabled": self.enabled,
            "features": list(self.features),
            "commands": list(self.commands),
            "constraints": dict(self.constraints),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Component:
        features = data.get("features") or []
        commands = data.get("commands") or []
        return cls(
            id=str(data.get("id") or ""),
            type=str(data.get("type") or ""),
            name=str(data.get("name") or ""),
            enabled=bool(data.get("enabled")),
            features=tuple(str(x) for x in features),
            commands=tuple(str(x) for x in commands),
            state=dict(data.get("state") or {}),
            constraints=dict(data.get("constraints") or {}),
            extra=_extra(
                data,
                {
                    "id",
                    "type",
                    "name",
                    "enabled",
                    "features",
                    "commands",
                    "state",
                    "constraints",
                },
            ),
        )


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    manufacturer: str
    series: str
    model: str
    online: bool
    role: str
    components: tuple[Component, ...]
    firmware_version: str | None = None
    hardware_version: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def component(self, component_id: str) -> Component | None:
        for item in self.components:
            if item.id == component_id:
                return item
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        comps = data.get("components") or []
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            manufacturer=str(data.get("manufacturer") or ""),
            series=str(data.get("series") or ""),
            model=str(data.get("model") or ""),
            online=bool(data.get("online")),
            role=str(data.get("role") or ""),
            components=tuple(
                Component.from_dict(c) for c in comps if isinstance(c, dict)
            ),
            firmware_version=str(data["firmware_version"]) if data.get("firmware_version") is not None else None,
            hardware_version=str(data["hardware_version"]) if data.get("hardware_version") is not None else None,
            diagnostics=dict(data.get("diagnostics") or {}),
            extra=_extra(
                data,
                {
                    "id",
                    "name",
                    "manufacturer",
                    "series",
                    "model",
                    "firmware_version",
                    "hardware_version",
                    "online",
                    "role",
                    "components",
                    "diagnostics",
                },
            ),
        )


@dataclass(frozen=True)
class DeviceSnapshot:
    protocol_version: str
    gateway_id: str
    revision: str
    devices: tuple[Device, ...]
    extra: dict[str, Any] = field(default_factory=dict)

    def device(self, device_id: str) -> Device | None:
        for item in self.devices:
            if item.id == device_id:
                return item
        return None

    def capabilities(self) -> list[dict[str, Any]]:
        rows = []
        for device in self.devices:
            for component in device.components:
                row = component.capabilities
                row["device_id"] = device.id
                rows.append(row)
        return rows

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceSnapshot:
        devices = data.get("devices") or []
        return cls(
            protocol_version=str(data.get("protocol_version") or ""),
            gateway_id=str(data.get("gateway_id") or ""),
            revision=str(data.get("revision") or ""),
            devices=tuple(Device.from_dict(d) for d in devices if isinstance(d, dict)),
            extra=_extra(data, {"protocol_version", "gateway_id", "revision", "devices"}),
        )


@dataclass(frozen=True)
class CommandResponse:
    request_id: str
    ok: bool
    status: str | None = None
    revision: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandResponse:
        err = data.get("error") if isinstance(data.get("error"), dict) else {}
        return cls(
            request_id=str(data.get("request_id") or ""),
            ok=bool(data.get("ok")),
            status=str(data["status"]) if data.get("status") is not None else None,
            revision=str(data["revision"]) if data.get("revision") is not None else None,
            error_code=str(err["code"]) if err.get("code") is not None else None,
            error_message=str(err["message"]) if err.get("message") is not None else None,
            error_details=dict(err.get("details") or {}),
            extra=_extra(data, {"request_id", "ok", "status", "revision", "error"}),
        )


EVENT_TYPES = frozenset(
    {
        "state_changed",
        "availability_changed",
        "topology_changed",
        "button_pressed",
        "scene_activated",
        "command_result",
        "server_restarting",
    }
)


RefreshReason = Literal["connected", "reconnected", "parse_error"]


@dataclass(frozen=True)
class SnapshotRefresh:
    """Public signal: caller must GET /api/v1/devices (clear ETag first).

    Yielded by `LanbonClient.listen()`. `listen_events()` skips these so old
    `async for Event` consumers keep working.
    """

    CONNECTED: ClassVar[str] = "connected"
    RECONNECTED: ClassVar[str] = "reconnected"
    PARSE_ERROR: ClassVar[str] = "parse_error"

    reason: RefreshReason

    @property
    def needs_snapshot(self) -> bool:
        return True


@dataclass(frozen=True)
class Event:
    protocol_version: str
    event_id: str
    revision: str
    type: str
    device_id: str | None = None
    component_id: str | None = None
    state: dict[str, Any] | None = None
    online: bool | None = None
    action: str | None = None
    request_id: str | None = None
    status: str | None = None
    error: dict[str, Any] | None = None
    timestamp: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_snapshot(self) -> bool:
        return self.type in {"topology_changed", "server_restarting"} or self.type not in EVENT_TYPES

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        return cls(
            protocol_version=str(data.get("protocol_version") or ""),
            event_id=str(data.get("event_id") or ""),
            revision=str(data.get("revision") or ""),
            type=str(data.get("type") or ""),
            device_id=str(data["device_id"]) if data.get("device_id") is not None else None,
            component_id=str(data["component_id"]) if data.get("component_id") is not None else None,
            state=dict(data["state"]) if isinstance(data.get("state"), dict) else None,
            online=bool(data["online"]) if data.get("online") is not None else None,
            action=str(data["action"]) if data.get("action") is not None else None,
            request_id=str(data["request_id"]) if data.get("request_id") is not None else None,
            status=str(data["status"]) if data.get("status") is not None else None,
            error=dict(data["error"]) if isinstance(data.get("error"), dict) else None,
            timestamp=str(data["timestamp"]) if data.get("timestamp") is not None else None,
            extra=_extra(
                data,
                {
                    "protocol_version",
                    "event_id",
                    "revision",
                    "type",
                    "timestamp",
                    "device_id",
                    "component_id",
                    "state",
                    "online",
                    "action",
                    "request_id",
                    "status",
                    "error",
                },
            ),
        )


@dataclass(frozen=True)
class DiscoveredGateway:
    host: str
    port: int
    gateway_id: str
    api: str
    path: str
    series: str
    model: str
    auth: str
    scheme: str
