from aiolanbon.discovery import discovered_from_mdns, parse_mdns_txt
from aiolanbon.models import Component, DeviceSnapshot, Event, GatewayInfo
from tests.mock_loip import INFO, SNAPSHOT, TOKEN


def test_mdns_drops_token_and_unknown():
    txt = parse_mdns_txt(
        {
            b"id": b"aabbccddeeff",
            b"api": b"1",
            b"path": b"/api/v1",
            b"series": b"L10",
            b"model": b"L10",
            b"auth": b"bearer",
            b"scheme": b"http",
            b"token": TOKEN.encode(),
            b"password": b"nope",
            b"extra": b"drop",
        }
    )
    assert txt["id"] == "aabbccddeeff"
    assert "token" not in txt
    assert "password" not in txt
    assert "extra" not in txt
    gw = discovered_from_mdns("192.168.0.155", 8765, {b"id": b"aabbccddeeff", b"token": TOKEN.encode()})
    assert gw.gateway_id == "aabbccddeeff"
    assert TOKEN not in repr(gw)


def test_info_and_capabilities_ignore_unknown_and_keep_series_as_data():
    info = GatewayInfo.from_dict({**INFO, "locale": "en"})
    assert info.series == "L10"
    assert info.extra["locale"] == "en"
    snap = DeviceSnapshot.from_dict(
        {
            **SNAPSHOT,
            "devices": [
                {
                    **SNAPSHOT["devices"][0],
                    "components": [
                        {
                            **SNAPSHOT["devices"][0]["components"][0],
                            "vendor_flag": True,
                        }
                    ],
                }
            ],
        }
    )
    comp: Component = snap.devices[0].components[0]
    assert comp.extra["vendor_flag"] is True
    caps = snap.capabilities()
    assert caps[0]["type"] == "switch"
    assert "series" not in caps[0]


def test_unknown_event_needs_snapshot():
    ev = Event.from_dict(
        {
            "protocol_version": "1.0.0",
            "event_id": "x",
            "revision": "9",
            "type": "topology_changed",
        }
    )
    assert ev.needs_snapshot is True
    ev2 = Event.from_dict(
        {
            "protocol_version": "1.0.0",
            "event_id": "y",
            "revision": "9",
            "type": "not_in_v1",
        }
    )
    assert ev2.needs_snapshot is True
