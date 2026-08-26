import pytest
from aiohttp import ClientSession, web

from tests.mock_loip import TOKEN, make_app


@pytest.fixture
async def loip_server():
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])
    async with ClientSession() as session:
        yield {"app": app, "port": port, "session": session, "token": TOKEN}
    await runner.cleanup()
