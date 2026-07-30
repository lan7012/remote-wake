#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中继服务器自测：验证魔法包格式 + 鉴权 + 转发。仅用标准库，无需联网。"""
import sys, os, socket, threading, json, time
import urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(__file__))
import relay_server
from http.server import ThreadingHTTPServer

MAC = "AA:BB:CC:DD:EE:FF"

def test_packet():
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', 9))
    srv.settimeout(3)
    relay_server.send_magic_packet(MAC, '127.0.0.1', 9)
    data, _ = srv.recvfrom(1024)
    assert len(data) == 102, f"长度应为102，实际 {len(data)}"
    assert data[:6] == b'\xff' * 6, "前6字节应为 0xFF 同步头"
    mac_bytes = bytes.fromhex(MAC.replace(':', ''))
    assert data.count(mac_bytes) == 16, "MAC 应重复16次"
    print("PASS  魔法包格式正确 (102字节, 同步头+16×MAC)")
    srv.close()

def test_server():
    cfg = dict(relay_server.DEFAULT_CONFIG)
    cfg['token'] = 'testtoken'
    cfg['broadcast'] = '127.0.0.1'
    cfg['port'] = 8099
    httpd = ThreadingHTTPServer(('127.0.0.1', 8099), relay_server.Handler)
    httpd.cfg = cfg
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', 9))
    srv.settimeout(3)

    # 正确 token
    req = urllib.request.Request(
        'http://127.0.0.1:8099/wake',
        data=json.dumps({'mac': MAC, 'token': 'testtoken'}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    body = json.loads(urllib.request.urlopen(req, timeout=3).read())
    assert body['ok'] is True, body
    data, _ = srv.recvfrom(1024)
    assert len(data) == 102
    print("PASS  服务器接受正确 token 并转发魔法包")

    # 错误 token
    req2 = urllib.request.Request(
        'http://127.0.0.1:8099/wake',
        data=json.dumps({'mac': MAC, 'token': 'wrong'}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        urllib.request.urlopen(req2, timeout=3)
        print("FAIL  错误 token 竟被接受")
    except urllib.error.HTTPError as e:
        assert e.code == 401, e.code
        print("PASS  服务器拒绝错误 token (HTTP 401)")
    srv.close()
    httpd.shutdown()

if __name__ == '__main__':
    test_packet()
    test_server()
    print("\nALL TESTS PASSED ✅")
