#!/usr/bin/env python3
"""Marionette 协议桩：验证 scripts/tab-guard.py 的握手、分帧与命令序列。

这一个桩不做任何浏览器操作，只按 Marionette 协议回包，用来在**没有 Firefox**
的机器上回归守护脚本的通信层（真实 Firefox 上的行为要在 Deck 上自测）。

用法:
    python3 tests/marionette-mock.py 2928 &
    python3 scripts/tab-guard.py --port 2928 --list
    python3 scripts/tab-guard.py --port 2928 --once
"""

import json
import socket
import sys
import threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2928
VERBOSE = "-v" in sys.argv

STATUS = {
    "ok": True,
    "gameFound": True,
    "created": False,
    "blocked": 2,
    "count": 2,
    "activeIndex": 0,
    "tabs": [
        {
            "i": 0,
            "title": "云·终末地",
            "host": "endfield.hypergryph.com",
            "url": "https://endfield.hypergryph.com/cloud",
            "pinned": True,
            "active": True,
            "game": True,
        },
        {
            "i": 1,
            "title": "误触网页",
            "host": "example.com",
            "url": "https://example.com/",
            "pinned": False,
            "active": False,
            "game": False,
        },
    ],
}


def read_message(conn, buf):
    while b":" not in buf:
        chunk = conn.recv(65536)
        if not chunk:
            return None, buf
        buf += chunk
    sep = buf.find(b":")
    length = int(buf[:sep])
    while len(buf) < sep + 1 + length:
        chunk = conn.recv(65536)
        if not chunk:
            return None, buf
        buf += chunk
    payload = buf[sep + 1 : sep + 1 + length]
    return json.loads(payload.decode("utf-8")), buf[sep + 1 + length :]


def handle(conn):
    hello = b'{"applicationType":"gecko","marionetteProtocol":3}'
    conn.sendall(("%d:" % len(hello)).encode() + hello)
    buf = b""
    while True:
        msg, buf = read_message(conn, buf)
        if msg is None:
            return
        mid, name, params = msg[1], msg[2], msg[3]
        if VERBOSE:
            extra = ""
            if name == "WebDriver:ExecuteScript":
                extra = " sandbox=%r newSandbox=%r scriptLen=%d" % (
                    params.get("sandbox"),
                    params.get("newSandbox"),
                    len(params.get("script", "")),
                )
            print("[mock] %s%s" % (name, extra), flush=True)
        if name == "WebDriver:NewSession":
            result = {"sessionId": "mock-session"}
        elif name == "WebDriver:SetContext":
            result = None
        elif name == "WebDriver:ExecuteScript":
            result = {"value": STATUS}
        else:
            result = None
        payload = json.dumps([1, mid, None, result]).encode("utf-8")
        conn.sendall(("%d:" % len(payload)).encode() + payload)


def main():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", PORT))
    srv.listen(5)
    print("[mock] listening on 127.0.0.1:%d" % PORT, flush=True)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
