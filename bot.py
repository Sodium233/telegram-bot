from config import CONFIG
from api import API
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

class TelegramBot:
    def __init__(self, api):
        self.api = api
    
        self.app = Application.builder().token(CONFIG["bot_token"]).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("update_schedule", self.update_schedule))

    async def run(self):
        print("Bot is running...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        try:
            await asyncio.Event().wait()
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
    
    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        await update.message.reply_text(
            "你好，我是 SodiumBot !"
        )
    
    async def update_schedule(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        try:
            await self.api.update_schedule()
            await update.message.reply_text(
                "课表更新完成"
            )
        except Exception as e:
            await update.message.reply_text(
                f"更新失败：{e}"
            )
    