#!/bin/sh
# 平板自测脚本：一键验证中继链路是否打通
# 用法：把 relay/ 传到平板后，在 Termux 里 cd 进该目录执行  sh verify_termux.sh
# 它会自动启动中继、做本机健康检查、发一次真实唤醒包，并把结果解读打印出来。
cd "$(dirname "$0")"

LOG="relay_test.log"
: > "$LOG" 2>/dev/null || true

# 从 config.json 读取端口与 token（避免手抄出错）
CFG_PORT=$(python -c "import json;print(json.load(open('config.json'))['port'])")
CFG_TOKEN=$(python -c "import json;print(json.load(open('config.json'))['token'])")
CFG_DEVICE=$(python -c "import json;d=json.load(open('config.json')).get('devices',{});print(next(iter(d.keys())) if d else 'pc1')")

echo "============================================"
echo " RemoteWake 中继自测"
echo " 端口=$CFG_PORT  token长度=${#CFG_TOKEN}  预设设备=$CFG_DEVICE"
echo "============================================"

# 启动中继（后台）
python relay_server.py > "$LOG" 2>&1 &
SRV_PID=$!
echo "[1/3] 已启动中继 (pid=$SRV_PID)，等待 2 秒..."
sleep 2

# 健康检查
echo "[2/3] 健康检查 /status :"
if curl -s "http://127.0.0.1:$CFG_PORT/status"; then
    echo ""
else
    echo ""
    echo "  !! 健康检查失败（服务可能没起来，看当前目录的 $LOG）"
fi

# 真实发一次唤醒包
echo "[3/3] 发送一次唤醒包到设备 '$CFG_DEVICE' :"
RESP=$(curl -s -X POST "http://127.0.0.1:$CFG_PORT/wake" \
  -H "Content-Type: application/json" \
  -d "{\"device\":\"$CFG_DEVICE\",\"token\":\"$CFG_TOKEN\"}" || echo '{"ok":false,"error":"curl failed"}')
echo "  返回: $RESP"

# 收尾
kill $SRV_PID 2>/dev/null || true
echo ""
echo "============================================"
echo " 怎么看结果："
echo " - /status 返回 {\"status\":\"ok\",...}  -> 中继已正常监听"
echo " - /wake 返回 {\"ok\":true,...}          -> 魔法包已发出（此时电脑应被唤醒/或已在开机）"
echo " - 若 /wake 返回 token 错误/401          -> config.json 的 token 与手机 App 填的不一致"
echo " - 若 /wake 返回 ok 但电脑没反应         -> 查 BIOS(Power On By PCI-E 开 / ErP 关) 与 MAC 是否正确"
echo "============================================"
