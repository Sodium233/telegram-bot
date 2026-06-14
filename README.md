# Telegram Schedule Bot

这是一个基于 Python、Playwright 和 Telegram Bot 的课程表抓取与 ICS 导出工具。

## 功能概览

- 登录教务系统并抓取课程表数据
- 将原始课表保存为 JSON
- 生成可导入的 ICS 日历文件
- 通过 Telegram Bot 命令触发更新
- 支持通过本地 HTTP 服务发布 ICS 文件

## 当前项目结构

- `main.py`：程序入口，初始化 JWClient、API、TelegramBot 和 ICS HTTP 服务
- `bot.py`：Telegram 命令处理逻辑（`/start`、`/myid`、`/update_schedule`）
- `api.py`：封装课表更新流程
- `jwclient.py`：与教务系统交互的核心客户端（登录、2FA、课表抓取）
- `webserver.py`：提供本地 HTTP 服务，暴露 `schedule.ics`
- `utils/gen_ics.py`：将 JSON 课表生成为 ICS
- `config.py`：加载 `config/config.json`
- `config/config.example.json`：配置模板
- `config/config.json`：真实配置文件（请勿提交）
- `data/`：保存 `schedule.json` 与 `schedule.ics`
- `browser_data/`：Chromium 持久化浏览器数据

## 准备工作

1. 使用项目虚拟环境安装依赖

   ```bash
   cd Developer/telegram-bot
   ./.venv/bin/python -m pip install -U pip
   ./.venv/bin/python -m pip install -r requirements.txt
   ./.venv/bin/python -m playwright install chromium
   ```

2. 复制并填写配置文件

   ```bash
   cp config/config.example.json config/config.json
   ```

   然后在 `config/config.json` 中填写：
   - `bot_token`：Telegram Bot Token
   - `my_user_id`：允许执行更新命令的 Telegram 用户 ID
   - `account.username`：学号
   - `account.password`：密码
   - `base_url` / `main_url`：教务系统入口地址
   - `schedule.xn` / `schedule.xq`：学年与学期
   - `schedule.first_day`：第一周周一日期（用于生成 ICS）
   - `output.path` / `output.schedule_file` / `output.ics_file`：输出路径

3. 如果你使用的是系统 Python，也可以在激活虚拟环境后运行：

   ```bash
   source .venv/bin/activate
   ```

## 启动方式

### 直接运行

当前入口文件为 `main.py`。它会同时启动：
- Telegram Bot
- 本地 ICS HTTP 服务（端口 8000）

推荐命令：

```bash
cd Developer/telegram-bot
./.venv/bin/python main.py
```

如果已激活虚拟环境，也可以直接运行：

```bash
python main.py
```

## 使用方式

启动后，可以向 Telegram Bot 发送：

- `/start`：查看欢迎信息
- `/myid`：查询当前 Telegram 用户 ID
- `/update_schedule`：立即抓取并更新课表（只有配置中的 `my_user_id` 才能执行）

更新完成后，输出文件会写入：

- `data/schedule.json`
- `data/schedule.ics`

当前程序会在本地启动 ICS HTTP 服务，访问地址为：

```text
http://127.0.0.1:8000/schedule.ics
```

如果需要在局域网内访问，可替换为服务器本机 IP。

## 注意事项

- 请不要提交真实的 `config/config.json`、Bot Token、账号密码或个人课表数据。
- 本项目已在 `.gitignore` 中忽略敏感配置、浏览器数据与生成结果。
- 如果教务系统启用了二次验证（2FA），Bot 会提示你输入 HIT App 验证码；验证码输入后会继续完成更新。
- 当前命令权限默认只开放给 `config/config.json` 中配置的 `my_user_id`。
- 生成的课表与 ICS 文件可能包含个人隐私信息，请谨慎分享与存储。
