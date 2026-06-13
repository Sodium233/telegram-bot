import asyncio
from api import API
from bot import TelegramBot
from jwclient import JWClient

async def main():
    jwc= JWClient()
    await jwc.initialize()

    api = API(jwc)
    bot = TelegramBot(api)

    
    await bot.run()

    # 防止程序退出
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
