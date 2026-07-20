from playwright.async_api import Playwright, async_playwright
from config import CONFIG
import exception
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
        self.xn = None
        self.xq = None
        self.first_monday = None


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

                for _ in range(100):   # 最多等待10秒
                    state = self.get_state()
                    if state == "logged_in":
                        print("登录成功")
                        return
                    if state == "need_2fa":
                        raise exception.Need2FAException()
                    await self.page.wait_for_timeout(100)
                
                # 超时
                if self.get_state() == "need_login":
                    if(await self.page.locator("#sliderDiv").is_visible()):
                        raise exception.LoginFailedException("登陆失败，检测到滑块验证")
                    else:
                        raise exception.LoginFailedException("登陆失败，请检查账号密码")
                raise RuntimeError(
                    f"登录状态未知: {self.page.url}"
                )
            elif state == "need_2fa":
                # 需要2fa验证
                print("需要2FA验证，正在处理2FA验证")
                await self.page.locator("#getDynamicCode").click()

                raise exception.Need2FAException()
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

    async def update_current_term(self):
        """
        更新当前学年学期
        """
        await self._ensure_login()
        response = await self.context.request.post(
            "https://jw.hitsz.edu.cn/component/querydangqianxnxq",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://jw.hitsz.edu.cn",
                "Referer": "https://jw.hitsz.edu.cn/authentication/main",
            }
        )
        if not response.ok:
            body = await response.text()
            raise RuntimeError(
                f"获取当前学年学期失败：HTTP {response.status}\n"
                f"响应内容：{body}"
            )
        result = await response.json()
        self.xn = result["XN"]
        self.xq = result["XQ"]
    
    async def update_current_first_monday(self):
        self.first_monday = await self.get_first_monday()

    async def _resolve_term(self, xn=None, xq=None):
        """
        解析要查询的学年学期。

        未传入参数时，使用当前学年学期。
        """
        if self.xn is None or self.xq is None:
            await self.update_current_term()

        query_xn = self.xn if xn is None else xn
        query_xq = self.xq if xq is None else xq

        return query_xn, query_xq

    async def get_schedule(self, xn=None, xq=None):
        await self._ensure_login()
        query_xn, query_xq = await self._resolve_term(xn, xq)

        response = await self.context.request.post(
            "https://jw.hitsz.edu.cn/xszykb/queryxszykbzong",
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
            form={
                "xn": query_xn,
                "xq": query_xq,
            }
        )

        if not response.ok:
            body = await response.text()
            raise RuntimeError(
                f"获取课表失败：HTTP {response.status}\n"
                f"响应内容：{body}"
            )

        return await response.json()

    async def get_gpa(self):
        """
        获取成绩。
        """
        await self._ensure_login()
        response = await self.context.request.post(
            "https://jw.hitsz.edu.cn/cjgl/grcjcx/getgpa",
            headers={
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        if not response.ok:
            body = await response.text()
            raise RuntimeError(
                f"获取GPA失败：HTTP {response.status}\n"
                f"响应内容：{body}"
            )
        
        return await response.json()
        
    async def get_scores(self, xn=None, xq=None):
        """
        获取课程成绩。
        Args:
            xn: 学年，例如 "2025-2026"。
            xq: 学期，例如 "1"、"2"、"3"。
                未传入时获取结果为全部学期课程成绩
        """
        await self._ensure_login()
        response = await self.context.request.post(
            "https://jw.hitsz.edu.cn/cjgl/grcjcx/grcjcx",
            headers={
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://jw.hitsz.edu.cn",
                "Referer": "https://jw.hitsz.edu.cn/authentication/main",
            },
            data={
                "xn": xn,
                "xq": xq,
                "kcmc": None,
                "cxbj": "-1",
                "pylx": "1",
                "current": 1,
                "pageSize": 100,
                "sffx": None,
                "yhdm":""
            }
        )
        if not response.ok:
            body = await response.text()
            raise RuntimeError(
                f"获取成绩失败：HTTP {response.status}\n"
                f"响应内容：{body}"
            )
        return await response.json()

    async def get_exam(self, xn=None, xq=None):
        """
        获取考试安排。
        """
        await self._ensure_login()
        query_xn, query_xq = await self._resolve_term(xn, xq)
        response = await self.context.request.post(
            "https://jw.hitsz.edu.cn/component/queryKsxxByXs",
            headers={
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        if not response.ok:
            body = await response.text()
            raise RuntimeError(
                f"获取考试安排失败：HTTP {response.status}\n"
                f"响应内容：{body}"
            )
        result = await response.json()
        return result

    async def get_first_monday(self, xn=None, xq=None):
        """
        根据学期获取第一个周一的日期
        """
        await self._ensure_login()
        query_xn, query_xq = await self._resolve_term(xn, xq)
        response = await self.context.request.post(
            "https://jw.hitsz.edu.cn/component/queryRlZcSj",
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://jw.hitsz.edu.cn",
                "Referer": "https://jw.hitsz.edu.cn/authentication/main",
            },
            form={
                "xn": query_xn,
                "xq": query_xq,
                "djz": "1"
            }
        )
        if not response.ok:
            body = await response.text()
            raise RuntimeError(
                f"获取{xn}学年{xq}学期第一个周一失败：HTTP {response.status}\n"
                f"响应内容：{body}"
            )
        result = await response.json()
        return result["content"][0]["rq"]

    async def get_latest_term_information(self):
        await self.update_current_term()
        await self.update_current_first_monday()
        return self.xn, self.xq, self.first_monday

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
    
    async def submit_2fa(self, code):
        # 需要2fa验证

        await self.page.locator("#dynamicCode").fill(code)
        await self.page.locator("#userNameDiv #reAuthSubmitBtn").click()
        
        if await self.page.locator("button.trust-device-sub-btn").count() > 0:
            await self.page.locator("button.trust-device-sub-btn").click()
            print("已信任当前设备")
            print("等待跳转至主页...")
            await self.page.wait_for_url(
                "**/authentication/main"
            )
        else:
            raise RuntimeError("2FA验证失败")

    async def close(self):
        await self._cleanup()