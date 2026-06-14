import asyncio
import re

from config import CONFIG
import exception
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

class TelegramBot:
    def __init__(self, api):
        self.api = api
        self.pending_2fa = {}

        self.app = Application.builder().token(CONFIG["bot_token"]).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("myid",self.myid))
        self.app.add_handler(CommandHandler("update_schedule", self.update_schedule))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.text_handler
            ))

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
    async def myid(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        await update.message.reply_text(
            f"你的User ID是：{update.effective_user.id}"
        )
    
    async def update_schedule(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        if update.effective_user.id!=CONFIG["my_user_id"]:
            print(update.effective_user.id)
            print(CONFIG["my_user_id"])
            await update.message.reply_text(
                "无权限访问"
            )
            return
        await update.message.reply_text("正在登录...")
        try:
            await self.api.update_schedule()
            await update.message.reply_text(
                "课表更新完成"
            )
        except exception.LoginFailedException as e:
            await update.message.reply_text(str(e))
        except exception.Need2FAException:
            await update.message.reply_text(
                "教务系统需要二次认证，请输入HIT App验证码（120秒内）："
            )
            # 从用户获取验证码
            try:
                code = await self.wait_for_2fa(update.effective_user.id)
                await update.message.reply_text("正在填入验证码...")
                await self.api.jw.submit_2fa(code)
            except asyncio.TimeoutError:
                await update.message.reply_text( "验证码超时，请重新执行/update_schedule")
                return
            except Exception as e:
                await update.message.reply_text(
                    f"发生错误：{e}"
                )   
                return
            await update.message.reply_text("正在保存课表数据...")
            await self.api.update_schedule()
            await update.message.reply_text("验证成功，课表更新完成")

        except Exception as e:
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                f"更新失败：{e}"
            )

    async def wait_for_2fa(self, user_id):
        future = asyncio.Future()
        self.pending_2fa[user_id] = future
        try:
            code = await asyncio.wait_for(
                future,
                timeout=120
            )
            return code
        finally:
            self.pending_2fa.pop(
                user_id,
                None
            )
    async def text_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        user_id = update.effective_user.id
        if user_id!=CONFIG["my_user_id"]:
            await update.message.reply_text("无权限访问")
            return

        future = self.pending_2fa.get(user_id)
        if not future:
            return

        await update.message.reply_text("正在处理验证码..")
        text = update.message.text.strip()
        if not re.fullmatch(r"\d{6}", text):
            await update.message.reply_text("请重新输入6位验证码。")
            return

        future.set_result(text)