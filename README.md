# aiolanbon

Company-private async client for **LOIP 1.0.0**. It talks to a LANBON gateway over local HTTP and optional WebSocket. It does not depend on Home Assistant and does not branch on L8/L9/L10.

Do not publish this package to PyPI, public GitHub, or a company Release without separate authorization.

```python
import os
import aiohttp
from aiolanbon import LanbonClient

token = os.environ["LOIP_TOKEN"]  # never hard-code or log

async with aiohttp.ClientSession() as session:
    client = LanbonClient("192.168.0.155", 8765, token, session)
    info = await client.get_info()
    snapshot = await client.get_devices()
```

- Auth: `Authorization: Bearer <token>` only.
- Events: `ws://host:port/api/v1/events` (no token in the URL). If `/info` says `polling`, use `get_devices` + revision instead.
- Capabilities: `snapshot.capabilities()` from each component's `features` / `commands` / `constraints`.
- mDNS: `_lanbon._tcp`, allowed TXT only (`id`, `api`, `path`, `series`, `model`, `auth`, `scheme`). Token is not read from TXT.

See `docs/MIGRATION.md` and `docs/LOIP_COVERAGE.md`.
