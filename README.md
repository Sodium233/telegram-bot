# Telegram Schedule Bot

这是一个基于 Python、Playwright 和 Telegram Bot 的课程表抓取与 ICS 导出工具。

## 功能简介

- 登录教务系统并抓取课表数据
- 将课程表保存为 JSON
- 生成可导入的 ICS 日历文件
- 通过 Telegram Bot 触发课表抓取与更新

## 项目结构

- `main.py`：Telegram Bot 入口
- `utils/accessSchedule.py`：抓取课程表数据
- `utils/generate_ics.py`：将 JSON 转为 ICS
- `config/config.example.json`：配置模板
- `data/`：保存抓取结果与生成的日历文件
- `browser_data/`：Chromium 持久化浏览器数据

## 快速开始

1. 安装依赖

   ```bash
   python -m pip install -U pip
   python -m pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. 配置账号与 Bot Token

   复制 `config/config.example.json` 为 `config/config.json`，并填写你的学号、密码、Telegram Bot Token 以及学年学期信息。

   ```bash
   cp config/config.example.json config/config.json
   ```

3. 运行程序

   ```bash
   python main.py
   ```

4. 输出结果

   - `data/schedule.json`
   - `data/schedule.ics`

## 上传到 GitHub 前的注意事项

- 请不要提交真实的 `config/config.json`、Bot Token、账号密码或个人课表数据。
- 本项目已在 `.gitignore` 中忽略上述敏感信息和运行生成文件。
- 如果登录过程需要二次验证（2FA），程序会在终端中提示输入验证码。
- 生成的课程表文件可能包含个人隐私信息，请谨慎处理。
