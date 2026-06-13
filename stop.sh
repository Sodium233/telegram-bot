#!/bin/bash

pkill -f "mihomo"
pkill -f "python3 main.py"
pkill -f "python3 -m http.server 8000"

echo "所有服务已停止"