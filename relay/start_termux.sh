#!/bin/sh
# 安卓平板(运行 Termux)启动中继服务器
# 用法：把 relay/ 目录传到平板后，在 Termux 里 cd 进该目录执行  sh start_termux.sh
#
# 说明：默认【不】获取 wakelock。中继是个网络监听服务，手机发来请求时
# Android 内核会自行唤醒进程处理，所以平板息屏/CPU 睡眠也能正常收命令，
# 没必要一直保持唤醒（更省电）。只要「关闭 Termux 的电池优化」即可常驻。
# 若你确实希望 CPU 始终不睡，可取消下面这行注释：
# termux-wake-lock 2>/dev/null
cd "$(dirname "$0")"
echo "[Termux] 启动中继（无需 wakelock，息屏也能收命令）..."
exec python relay_server.py "$@"
