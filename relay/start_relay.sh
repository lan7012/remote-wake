#!/usr/bin/env bash
# 远程开机中继服务器 - Linux / macOS / 树莓派 启动脚本
# 用法：chmod +x start_relay.sh && ./start_relay.sh
# 建议用 supervisor / systemd 让它开机自启（见 docs/SETUP.md）
cd "$(dirname "$0")"
python3 relay_server.py --config config.json
