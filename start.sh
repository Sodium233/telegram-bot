#!/bin/bash

# 出错立即退出
set -e

# 切换到项目目录
cd /home/yaju/Developer/telegram-bot

# 杀掉旧进程（可选）
pkill -f "mihomo" || true
pkill -f "python3 main.py" || true
pkill -f "python3 -m http.server 8000" || true

# 启动 mihomo
cd /home/yaju/mihomo
nohup ./mihomo -f /home/yaju/mihomo/config.yaml \
    > /home/yaju/mihomo/mihomo.log 2>&1 &

# 等待代理启动
sleep 3

# 设置代理环境变量
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
export ALL_PROXY=socks5://127.0.0.1:7897

# 回到项目目录
cd /home/yaju/Developer/telegram-bot

# 激活虚拟环境
source .venv/bin/activate

# 启动 Telegram Bot
nohup python3 main.py \
    > bot.log 2>&1 &

# 启动 ICS 文件发布
cd data
nohup python3 -m http.server 8000 \
    > ../http.log 2>&1 &

echo "=========================="
echo "mihomo 已启动"
echo "Telegram Bot 已启动"
echo "ICS HTTP 服务已启动"
echo "ICS 地址："
echo "http://<你的IP>:8000/schedule.ics"
echo "=========================="