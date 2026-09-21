# aiolanbon

Async Python client for **LOIP 1.0.0**. It talks to a LANBON gateway over local HTTP and optional WebSocket. It does not depend on Home Assistant and does not branch on L8/L9/L10.

```python
import os
import aiohttp
from aiolanbon import LanbonClient

token = os.environ["LOIP_TOKEN"]  # never hard-code or log

async with aiohttp.ClientSession() as session:
    client = LanbonClient("192.168.0.10", 8765, token, session)
    info = await client.get_info()
    snapshot = await client.get_devices()
```

- Auth: `Authorization: Bearer <token>` only.
- Events: `ws://host:port/api/v1/events` (no token in the URL).
- mDNS: `_lanbon._tcp`. Token is not read from TXT.

PyPI: `aiolanbon==0.2.0` (LOIP). `0.1.0` was the Mesh client.


Version 0.2.1 adds IPv6-safe HTTP and WebSocket URL construction. Release candidates must pass the Linux test matrix before publication.
