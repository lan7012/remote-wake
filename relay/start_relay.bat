@echo off
REM 远程开机中继服务器 - Windows 启动脚本
REM 用法：双击运行，或命令行 python relay_server.py
cd /d "%~dp0"
python relay_server.py --config config.json
pause
