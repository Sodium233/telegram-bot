from playwright.async_api import Playwright, async_playwright
from config import CONFIG
import json
import utils.generate_ics as ics_gen

def get_state(page):
    if page.url.endswith("/authentication/main"):
        return "logged_in"
    elif page.url.endswith("/authserver/login?service=http%3A%2F%2Fjw.hitsz.edu.cn%2FcasLogin"):
        return "need_login"
    elif page.url.endswith("authserver/reAuthCheck/reAuthLoginView.do?isMultifactor=true&service=http%3A%2F%2Fjw.hitsz.edu.cn%2FcasLogin"):
        return "need_2fa"
    else:
        return "unknown"

async def accessScheduleData(playwright: Playwright):
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir="./browser_data",
        channel="chrome",
        headless=True,
    )
    page = await context.new_page()
    print("1", flush=True)
    await page.goto(CONFIG["base_url"], wait_until="networkidle")
    print("URL:", page.url, flush=True)
    print("2", page.url, flush=True)
    await page.locator(".towlg_tybox").click()
    print("3", page.url, flush=True)
    # 状态机，判断当前页面状态，决定下一步操作
    while True:
        state = get_state(page)
        print("当前页面状态:", state, flush=True)
        if state == "logged_in":
            print("登陆成功")
            break
        elif state == "need_login":
            # 需要输入账号密码
            print("需要登录，正在输入账号密码")
            print(await page.locator("#username").count())
            print(await page.locator("#password").count())
            await page.screenshot(path="login.png")
            await page.locator("#username").first.fill(CONFIG["account"]["username"])
            await page.locator("#password").first.fill(CONFIG["account"]["password"])
            await page.locator("#rememberMe").check()
            await page.locator("a#login_submit").click()
            await page.wait_for_load_state()
            continue
        elif state == "need_2fa":
            # 需要2fa验证
            print("需要2FA验证，正在处理2FA验证")
            await page.locator("#getDynamicCode").click()
            code = input("请输入2FA验证码: ")
            await page.locator("#dynamicCode").fill(code)
            await page.locator("#userNameDiv #reAuthSubmitBtn").click()

            if await page.locator("button.trust-device-sub-btn").count() > 0:
                await page.locator("button.trust-device-sub-btn").click()
                print("已信任当前设备")
            await page.wait_for_url(
                "**/authentication/main"
            )
            continue;
                
        else:
            print("未知页面状态，无法继续操作")
            await context.close()
            return None

    # ---------------------
    data = {
        "xn": CONFIG["schedule"]["xn"],
        "xq": CONFIG["schedule"]["xq"],
    }
    schedule = await page.evaluate(
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
     data)
    await context.close()
    return schedule

async def accessSchedule():
    async with async_playwright() as playwright:
        schedule = await accessScheduleData(playwright)

    with open(CONFIG["output"]["schedule_file"], "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=4)


async def saveSchedule():
    # 访问教务系统获取课表数据
    await accessSchedule()
    # 生成课表ICS文件
    ics_gen.generate_ics_from_json(
        CONFIG['output']['schedule_file'],
        CONFIG['schedule']['first_day'],
        CONFIG['output']['ics_file']
    )
    print(f"课表已保存到 {CONFIG['output']['schedule_file']} 和 {CONFIG['output']['ics_file']}")