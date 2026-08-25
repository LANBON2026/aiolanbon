import logging

import pytest

from aiolanbon import LanbonClient
from aiolanbon._redact import redact_text
from tests.mock_loip import TOKEN


def test_redact_bearer_and_query():
    text = f"Authorization: Bearer {TOKEN} url=ws://h/api/v1/ws?token={TOKEN}&x=1"
    out = redact_text(text, TOKEN)
    assert TOKEN not in out
    assert "Bearer <redacted>" in out
    assert "token=<redacted>" in out


def test_client_repr_and_events_url_hide_token():
    class _Sess:
        pass

    c = LanbonClient("192.168.0.155", 8765, TOKEN, _Sess())  # type: ignore[arg-type]
    assert TOKEN not in repr(c)
    assert "token" not in c.events_url
    assert TOKEN not in c.events_url


async def test_auth_error_does_not_include_token(loip_server, caplog):
    caplog.set_level(logging.DEBUG)
    c = LanbonClient("127.0.0.1", loip_server["port"], TOKEN + "ff", loip_server["session"])
    with pytest.raises(Exception) as ei:
        await c.get_info()
    assert TOKEN not in str(ei.value)
    assert TOKEN not in caplog.text
    assert TOKEN + "ff" not in str(ei.value)
