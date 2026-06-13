from playwright.async_api import Playwright, async_playwright
from config import CONFIG
import json

class JWClient:

    def __init__(self):
        # 账号信息
        self.username = CONFIG["account"]["username"]
        self.password = CONFIG["account"]["password"]

        # Playwright对象
        self.playwright = None
        self.context = None
        self.page = None
        self.data = {
            "xn": CONFIG["schedule"]["xn"],
            "xq": CONFIG["schedule"]["xq"],
        }

    async def initialize(self):
        if self.playwright: #防止重复创建
            return
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            channel="chrome",
            headless=True,
        )
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        await self.page.goto(CONFIG["base_url"], wait_until="networkidle")

    async def _login(self):
        await self.page.goto(CONFIG["base_url"], wait_until="networkidle")  # 跳转到本研初始界面
        print("1", self.page.url, flush=True)
        await self.page.locator(".towlg_tybox").click()
        print("2", self.page.url, flush=True)
        print("正在登录....")
        # 状态机，判断当前页面状态，决定下一步操作
        while True:
            state = self.get_state()
            print("当前页面状态:", state, flush=True)
            if state == "logged_in":
                print("登陆成功")
                break
            elif state == "need_login":
                # 需要输入账号密码
                print("需要登录，正在输入账号密码")
                print(await self.page.locator("#username").count())
                print(await self.page.locator("#password").count())
                await self.page.screenshot(path="login.png")
                await self.page.locator("#username").first.fill(self.username)
                await self.page.locator("#password").first.fill(self.password)
                await self.page.locator("#rememberMe").check()
                await self.page.locator("a#login_submit").click()
                await self.page.wait_for_load_state("networkidle")
                continue
            elif state == "need_2fa":
                # 需要2fa验证
                print("需要2FA验证，正在处理2FA验证")
                await self.page.locator("#getDynamicCode").click()
                code = input("请输入2FA验证码: ")
                await self.page.locator("#dynamicCode").fill(code)
                await self.page.locator("#userNameDiv #reAuthSubmitBtn").click()

                if await self.page.locator("button.trust-device-sub-btn").count() > 0:
                    await self.page.locator("button.trust-device-sub-btn").click()
                    print("已信任当前设备")
                print("等待跳转至主页...")
                await self.page.wait_for_url(
                    "**/authentication/main"
                )
                continue
            elif state == "session_invalid":    # 一般出现于直接访问主页但是会话失效的情况，由于开始时直接跳转到了初始页面，所以一般不会出现这种情况
                # 会话过期，重新登陆
                await self.page.locator(".towlg_tybox").click()     # 点击进入登录界面，应该会跳转到need_login界面
                await self.page.wait_for_load_state("networkidle")
                continue
            else:
                print("未知页面状态，无法继续操作")
                raise RuntimeError(f"Unknown state: {self.page.url}")

    async def _ensure_login(self):
        """
        保证当前已经登录。
        职责：尝试跳转到主页，如果不是教务平台主页(logged_in)，重新登陆
        """
        await self.page.goto(CONFIG["main_url"], wait_until="networkidle")
        if self.get_state()!="logged_in":
            # 不是登录界面，直接重新登录
            await self._login()
        


    async def _cleanup(self):
        if self.context:
            await self.context.close()
            self.context = None
            self.page = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def get_schedule(self):
        """
        获取课表。
        """
        try:
            await self._ensure_login()
            schedule_data = await self.page.evaluate(
                """
                async (data) => {
                    const response = await fetch(
                        "/xszykb/queryxszykbzong",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type": 
                                "application/x-www-form-urlencoded"
                            },
                            body: new URLSearchParams(data)
                        }
                    );
                    return await response.json();
                }
                """,
            self.data)
        except Exception as e:
            print(e)
            return None
        return schedule_data

    async def get_score(self):
        """
        获取成绩。
        """
        try:
            await self._ensure_login()

            # 以后实现

            pass
        except Exception as e:
            print(e)
            return None
        


    async def get_exam(self):
        """
        获取考试安排。
        """
        try:
            await self._ensure_login()

            # 以后实现

            pass
        except Exception as e:
            print(e)
            return None
        

    def get_state(self):
        if self.page.url.endswith("/session/invalid"):
            return "session_invalid"
        elif self.page.url.endswith("/authentication/main"):
            return "logged_in"
        elif self.page.url.endswith("/authserver/login?service=http%3A%2F%2Fjw.hitsz.edu.cn%2FcasLogin"):
            return "need_login"
        elif self.page.url.endswith("authserver/reAuthCheck/reAuthLoginView.do?isMultifactor=true&service=http%3A%2F%2Fjw.hitsz.edu.cn%2FcasLogin"):
            return "need_2fa"
        else:
            return "unknown"
    async def close(self):
        await self._cleanup()