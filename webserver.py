from aiohttp import web
from pathlib import Path

class WebServer:
    def __init__(self):
        self.app = web.Application()
        self.app.router.add_get(
            "/schedule.ics",
            self.get_schedule
        )

        self.runner = None
    async def get_schedule(self, request):
        return web.FileResponse(
            Path("./data/schedule.ics")
        )
    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(
            self.runner,
            host="0.0.0.0",
            port=8000
        )

        await site.start()

        print("Web server running on port 8000")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()