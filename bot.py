import asyncio
import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

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
        self.app.add_handler(CommandHandler("update_calendar", self.update_calendar))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.text_handler
            ))
        self.app.add_handler(CommandHandler("today_schedule",self.today_schedule))
        self.app.add_handler(CommandHandler("gpa",self.gpa))
        self.app.add_handler(CommandHandler("score",self.score))


    async def run(self):
        print("Bot is running...")
        await self.app.initialize()
        self.app.job_queue.run_daily(
            self.update_calendar_job,
            time=time(hour=23, minute=19,tzinfo=ZoneInfo("Asia/Shanghai"))
        )
        await self.app.start()

        await self.app.updater.start_polling()

        try:
            await asyncio.Event().wait()

        except Exception as e:
            print("Bot stopped:", e)

        finally:
            if self.app.updater.running:
                await self.app.updater.stop()

            if self.app.running:
                await self.app.stop()

            await self.app.shutdown()
    
    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        await update.message.reply_text(
            "你好，我是 SodiumBot !\n"
            "目前我的功能如下\n"
            "/myid  获得你的id\n"
            "/update_calendar  更新课表数据，可在10.249.61.82:8000/schedule.ics获得课表\n"
            "/today_schedule    从已保存的课表数据中获取今日日程\n"
            "/gpa   获取当前gpa数据\n"
            "/score 获取成绩，如/score all或/score 2025-2026 2"
        )
        return
    async def myid(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        await update.message.reply_text(
            f"你的User ID是：{update.effective_user.id}"
        )
        return
    
    async def update_calendar(
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
            await self.api.update_calendar()
            await update.message.reply_text(
                "日历更新完成"
            )
            xn, xq, first_monday = self.api.get_current_term_information()
            await update.message.reply_text(
                f"当前为：{xn} 学年第 {xq} 学期\n"
                f"开学时间为：{first_monday}"
            )
            return
        except exception.LoginFailedException as e:
            await update.message.reply_text(str(e))
            return
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
            await update.message.reply_text("正在保存课程、考试数据...")
            await self.api.update_calendar()
            await update.message.reply_text("验证成功，日历更新完成")
            return

        except Exception as e:
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                f"发生错误：{e}"
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

    async def today_schedule(self, update:Update, context: ContextTypes.DEFAULT_TYPE):
        today_schedule = self.api.get_today_schedule()
        if not today_schedule:
            await update.message.reply_text("今日无事项")
            return
        else:
            courses = sorted(
                today_schedule,
                key=lambda c: c["start"]
            )
            msg = ""
            for course in courses:
                start = datetime.fromisoformat(course["start"])
                end = datetime.fromisoformat(course["end"])

                msg += (
                    f"{course['title']}\n"
                    f"{start:%H:%M} - {end:%H:%M}\n"
                    f"{course['location']}\n\n"
                )
            await update.message.reply_text(msg)
            return
    
    async def gpa(self, update:Update, context: ContextTypes.DEFAULT_TYPE):
        gpa = await self.api.get_gpa()
        msg = (
            f"核心课程学分绩：{gpa['PJXFJ']}\n"
            f"排名范围：{gpa['PJXFJ_PM_FW']}%  （{gpa['PJXFJ_PM']}/{gpa['ZRS']}）\n"
            f"全部课程GPA：{gpa['GPA_QBJQKC']}\n"
            f"排名范围：{gpa['GPA_QBJQKC_PM_FW']}%  （{gpa['GPA_QBJQKC_PM']}/{gpa['ZRS']}）\n"
        )
        await update.message.reply_text(msg)
    
    async def score(self, update:Update, context: ContextTypes.DEFAULT_TYPE):
        arg = " ".join(context.args)
        if not arg:
            await update.message.reply_text(
                "/score 的用法如下\n"
                "/score all  查询全部课程的成绩\n"
                "/score [学期] 查询某学期的课程，如/score 2025-2026 1"
            )
            return
        if context.args[0] == "all":
            scores = await self.api.get_scores()
        else:
            m = re.match(r"^(\d{4}-\d{4})\s([123])$", arg.strip())
            if not m:
                await update.message.reply_text(
                    "输入格式错误！"
                    "/score 的用法如下\n"
                    "/score all  查询全部课程的成绩\n"
                    "/score [学期] 查询某学期的课程，如/score 2025-2026 1/2/3"
                )
                return
            xn = m.group(1)
            xq = m.group(2)
            scores = await self.api.get_scores(xn,xq)
            

        if not scores:
            await update.message.reply_text("未查询到成绩！")
            return
        else:
            msg = ""
            count = 0;
            for item in scores['content']['list']:
                name = item.get("kcmc")     # 课程名称
                score = item.get("zpcj")    # 总成绩
                rank = int(item.get("pm"))
                total_num = int(item.get("zrs"))
                credit = item.get("xf")     # 学分
                hour = item.get("xs")       # 学时
                course_type = item.get("khfs")  # 考试/考察课
                count = count+1
                msg += (
                    f"课程名称：{name}（{course_type}）\n"
                    f"总评成绩：{score} \n"
                    f"排名范围：{round(rank/total_num *100,2)}%（{rank}/{total_num}）\n"
                    f"学分：{credit}  学时：{hour}\n\n"
                )
            msg += (f"总共查询到 {count} 门课程的成绩\n")
            await update.message.reply_text(msg)
            return
        
    async def update_calendar_job(
        self,
        context: ContextTypes.DEFAULT_TYPE
    ):
        try:
            print("开始自动更新课表")

            await self.api.update_calendar()

            await context.bot.send_message(
                chat_id=CONFIG["my_user_id"],
                text="课表自动更新完成"
            )

        except exception.LoginFailedException as e:
            await context.bot.send_message(
                chat_id=CONFIG["my_user_id"],
                text=f"自动更新失败：{e}"
            )

        except exception.Need2FAException:
            await context.bot.send_message(
                chat_id=CONFIG["my_user_id"],
                text="自动更新失败：教务系统需要二次认证"
            )

        except Exception as e:
            await context.bot.send_message(
                chat_id=CONFIG["my_user_id"],
                text=f"自动更新异常：{e}"
            )