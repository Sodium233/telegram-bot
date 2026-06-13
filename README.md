# Telegram Schedule Bot

这是一个基于 Python、Playwright 和 Telegram Bot 的课程表抓取与 ICS 导出工具。

## 功能概览

- 登录教务系统并抓取课程表数据
- 将原始课表保存为 JSON
- 生成可导入的 ICS 日历文件
- 通过 Telegram Bot 命令触发更新
- 支持通过本地 HTTP 服务发布 ICS 文件

## 当前项目结构

- `main.py`：程序入口，初始化 JWClient、API 和 TelegramBot
- `bot.py`：Telegram 命令处理逻辑（`/start`、`/update_schedule`）
- `api.py`：封装课表更新流程
- `jwclient.py`：与教务系统交互的核心客户端
- `utils/gen_ics.py`：将 JSON 课表生成为 ICS
- `config/config.example.json`：配置模板
- `config/config.json`：真实配置文件（请勿提交）
- `data/`：保存 `schedule.json` 与 `schedule.ics`
- `browser_data/`：Chromium 持久化浏览器数据

## 准备工作

1. 安装 Python 依赖

   ```bash
   python -m pip install -U pip
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. 配置账号与 Bot Token

   ```bash
   cp config/config.example.json config/config.json
   ```

   然后在 `config/config.json` 中填写：
   - `bot_token`：Telegram Bot Token
   - `account.username`：学号
   - `account.password`：密码
   - `schedule.xn` / `schedule.xq`：学年与学期
   - `schedule.first_day`：第一周周一日期（用于生成 ICS）

3. 进入虚拟环境（如果项目已经准备好）

   ```bash
   source .venv/bin/activate
   ```

## 启动方式

### 方式一：直接运行

```bash
python main.py
```

### 方式二：使用启动脚本

项目中提供了 `start.sh` / `stop.sh`，会一并启动：
- mihomo 代理
- Telegram Bot
- 本地 ICS HTTP 服务

```bash
bash start.sh
```

停止服务：

```bash
bash stop.sh
```

## 使用方式

启动后，可以向 Telegram Bot 发送：

- `/start`：查看欢迎信息
- `/update_schedule`：立即抓取并更新课表

更新完成后，输出文件会写入：

- `data/schedule.json`
- `data/schedule.ics`

如果启用了 `start.sh`，ICS 文件也可以通过本地 HTTP 服务访问，例如：

```text
http://<你的IP>:8000/schedule.ics
```

## 注意事项

- 请不要提交真实的 `config/config.json`、Bot Token、账号密码或个人课表数据。
- 本项目已在 `.gitignore` 中忽略敏感配置、浏览器数据与生成结果。
- 如果教务系统启用了二次验证（2FA），程序会在终端中提示输入验证码。
- 生成的课表与 ICS 文件可能包含个人隐私信息，请谨慎分享与存储。
