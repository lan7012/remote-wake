#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程开机 · 中继服务器 (Wake-on-LAN Relay)

作用：
    跑在「家里局域网、常年开机」的一台设备上（树莓派 / 旧电脑 / NAS / 软路由均可）。
    手机在任意网络下访问本服务器的 /wake 接口，由本机在局域网内把 WoL 魔法包发给目标电脑。

依赖：仅 Python 标准库，无需 pip 安装任何东西（Python 3.7+）。

启动：
    python relay_server.py
    或指定配置：  python relay_server.py --config config.json

接口：
    POST /wake        body: {"mac":"AA:BB:CC:DD:EE:FF","token":"你的令牌"}
    GET  /wake?mac=AA:BB:CC:DD:EE:FF&token=你的令牌
    GET  /status      健康检查，返回 {"ok":true}
"""

import argparse
import json
import os
import re
import socket
import struct
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DEFAULT_CONFIG = {
    "host": "0.0.0.0",          # 监听地址，0.0.0.0 表示接受所有网卡
    "port": 8080,                # 对外端口（路由器需把此外网端口转发到本机）
    "token": "CHANGE_ME_TOKEN",  # 访问令牌，手机端填同一个值
    # 广播地址：填 "auto" 时自动探测本机所在局域网的子网广播（安卓平板/Termux 推荐）；
    # 也可填具体地址如 "192.168.1.255"，或保留 "255.255.255.255"。
    "broadcast": "auto",
    "wol_port": 9,               # 魔法包目标端口，通常 7 或 9
    "use_ssl": False,            # 是否启用 HTTPS（强烈建议外网开启）
    "certfile": "",              # SSL 证书路径（use_ssl=true 时必填）
    "keyfile": "",               # SSL 私钥路径
    # 可选：预设设备，手机只传 device 名字即可，例如 POST {"device":"pc1","token":"..."}
    "devices": {
        # "pc1": "AA:BB:CC:DD:EE:FF"
    }
}


def _local_ip_via_socket():
    """UDP 连接外网（不真正发送数据），获取本机在默认路由上的 IP。

    在 Termux/安卓等没有 ip/ifconfig 命令的环境里，这是探测本机局域网 IP
    最可靠的零依赖方法。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 53))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def _broadcast_from_ip(ip, prefix):
    """根据 IP 和前缀长度计算子网广播地址。"""
    ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
    mask = ((1 << 32) - 1) ^ ((1 << (32 - prefix)) - 1)
    net = ip_int & mask
    return socket.inet_ntoa(struct.pack("!I", net | (~mask & 0xFFFFFFFF)))


def _detect_broadcasts():
    """尽力探测本机所在局域网的子网广播地址（安卓/Termux 等 Wi-Fi 环境下很关键）。"""
    broadcasts = set()

    # 1. 先尝试系统命令（Linux/树莓派等通常可用）
    out = ""
    for cmd in (["ip", "-4", "addr", "show", "up"], ["ifconfig", "-a"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
            if out and "inet " in out:
                break
        except Exception:
            out = ""
    for m in re.finditer(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", out):
        ip = m.group(1)
        prefix = int(m.group(2))
        if ip.startswith("127.") or prefix <= 0 or prefix > 32:
            continue
        try:
            broadcasts.add(_broadcast_from_ip(ip, prefix))
        except Exception:
            pass

    # 2. 安卓/Termux 常常没有 ip/ifconfig，用 socket 取本机默认 IP 并推断 /24 广播
    if not broadcasts:
        local_ip = _local_ip_via_socket()
        if local_ip and not local_ip.startswith("127."):
            try:
                broadcasts.add(_broadcast_from_ip(local_ip, 24))
            except Exception:
                pass
    return sorted(broadcasts)


def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)
            cfg.update(user)
            print(f"[配置] 已加载配置文件: {path}")
        except Exception as e:
            print(f"[警告] 读取配置失败，使用默认配置: {e}")
    else:
        print("[配置] 未提供/找不到配置文件，使用默认配置")

    # 允许 config.user.json 覆盖，避免更新 zip 时覆盖用户的 token/MAC 等私有配置
    user_path = os.path.join(os.path.dirname(os.path.abspath(path)) or ".", "config.user.json")
    if os.path.exists(user_path):
        try:
            with open(user_path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
            print(f"[配置] 已加载用户覆盖配置: {user_path}")
        except Exception as e:
            print(f"[警告] 读取用户覆盖配置失败: {e}")
    return cfg


def send_magic_packet(mac, broadcast, port):
    """构造并发送 Wake-on-LAN 魔法包。

    会向多个目标地址各发一份（子网广播 + 全网广播），任一成功即可，
    确保安卓平板等 Wi-Fi 设备也能把包可靠地送到同局域网电脑。
    """
    mac_clean = mac.replace(":", "").replace("-", "").replace(".", "")
    if len(mac_clean) != 12:
        raise ValueError(f"MAC 地址格式不正确: {mac}")
    try:
        mac_bytes = bytes.fromhex(mac_clean)
    except ValueError:
        raise ValueError(f"MAC 地址包含非法字符: {mac}")

    packet = b"\xff" * 6 + mac_bytes * 16

    targets = set()
    b = (broadcast or "").strip().lower()
    if b and b != "auto":
        targets.add(broadcast.strip())
    if not b or b == "auto":
        for auto in _detect_broadcasts():
            targets.add(auto)
    targets.add("255.255.255.255")  # 全子网广播兜底

    sent = []
    for tgt in targets:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (tgt, int(port)))
            sock.close()
            sent.append(tgt)
        except Exception:
            # 单个地址失败不影响其它地址，继续尝试
            pass
    if not sent:
        raise RuntimeError("无法向任何广播地址发送魔法包（请检查网络是否连通）")
    return sent


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _resolve_mac(self, mac, device):
        cfg = self.server.cfg
        if device:
            if device in cfg.get("devices", {}):
                return cfg["devices"][device]
            raise ValueError(f"未知设备名: {device}")
        if not mac:
            raise ValueError("缺少 mac 或 device 参数")
        return mac

    def _discard_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            try:
                self.rfile.read(length)
            except Exception:
                pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/status"):
            self._json({"ok": True, "service": "remotewake-relay"})
            return
        if parsed.path == "/wake":
            qs = parse_qs(parsed.query)
            mac = (qs.get("mac") or [None])[0]
            device = (qs.get("device") or [None])[0]
            token = (qs.get("token") or [None])[0]
            self._handle_wake(mac, device, token)
            return
        self._discard_body()
        self.close_connection = 1
        self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/wake":
            self._discard_body()
            self.close_connection = 1
            self._json({"ok": False, "error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}
        mac = body.get("mac")
        device = body.get("device")
        token = body.get("token")
        self._handle_wake(mac, device, token)

    def _handle_wake(self, mac, device, token):
        cfg = self.server.cfg
        if token != cfg["token"]:
            self._json({"ok": False, "error": "token 校验失败"}, 401)
            return
        try:
            resolved = self._resolve_mac(mac, device)
            targets = send_magic_packet(resolved, cfg["broadcast"], int(cfg["wol_port"]))
            print(f"[唤醒] 已向 {resolved} 发送魔法包 (目标: {', '.join(targets)}:{cfg['wol_port']})")
            self._json({"ok": True, "mac": resolved, "targets": targets})
        except Exception as e:
            print(f"[错误] 发送失败: {e}")
            self._json({"ok": False, "error": str(e)}, 400)

    # 静默日志，避免刷屏
    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="远程开机中继服务器")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f"[启动] 监听 {cfg['host']}:{cfg['port']}  token长度={len(cfg['token'])}")
    if cfg["broadcast"].strip().lower() == "auto":
        detected = _detect_broadcasts()
        print(f"[启动] 自动探测子网广播: {detected if detected else '未探测到，将使用 255.255.255.255'}")

    httpd = ThreadingHTTPServer((cfg["host"], int(cfg["port"])), Handler)
    httpd.cfg = cfg

    if cfg.get("use_ssl"):
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cfg["certfile"], cfg["keyfile"])
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        print("[启动] 已启用 HTTPS")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[停止] 服务器已关闭")
        httpd.server_close()


if __name__ == "__main__":
    main()
