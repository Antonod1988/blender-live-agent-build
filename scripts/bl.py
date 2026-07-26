"""Minimal client for the Blender MCP Bridge (newline-delimited JSON over TCP)."""
import json
import socket
import sys
import uuid

HOST, PORT = "127.0.0.1", 9876


def send(command, params=None, timeout=600):
    req = {"id": uuid.uuid4().hex[:8], "command": command, "params": params or {}}
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.settimeout(timeout)
    try:
        s.sendall(json.dumps(req).encode() + b"\n")
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        return json.loads(buf.split(b"\n", 1)[0])
    finally:
        s.close()


def run_file(path, timeout=600):
    with open(path, encoding="utf-8") as f:
        code = f.read()
    return send("python.execute", {"code": code, "timeout_seconds": min(timeout, 300)}, timeout)


def run_file_async(path, timeout=3600):
    with open(path, encoding="utf-8") as f:
        code = f.read()
    return send("python.execute_async", {"code": code, "timeout_seconds": timeout}, 30)


if __name__ == "__main__":
    if sys.argv[1] == "exec":
        r = run_file(sys.argv[2])
    elif sys.argv[1] == "execa":
        r = run_file_async(sys.argv[2])
    elif sys.argv[1] == "job":
        r = send("job.status", {"job_id": sys.argv[2]}, 30)
    else:
        r = send(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    print(json.dumps(r, ensure_ascii=False, indent=2)[:6000])
