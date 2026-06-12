from config import CONFIG
import utils.accessSchedule as accessSchedule

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

async def start(update, context):
    await update.message.reply_text(
        "你好，我是 SodiumBot !"
    )

async def loadSchedule(update, context):
    await accessSchedule.saveSchedule()
    await update.message.reply_text("已抓取课表")

def main():
    app = Application.builder().token(CONFIG["bot_token"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("load_schedule", loadSchedule))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}")
