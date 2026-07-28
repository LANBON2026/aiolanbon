# aiolanbon

Async Python client for the LANBON Mesh root local HTTP/WebSocket API (`proto: 1`).

```python
import aiohttp
from aiolanbon import LanbonClient

async with aiohttp.ClientSession() as session:
    client = LanbonClient("192.168.0.10", 8765, "token", session)
    info = await client.get_info()
```
