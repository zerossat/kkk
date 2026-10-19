#!/usr/bin/env python3
"""Low-rate diagnostics for an authorized Minecraft Java (Paper/Spigot) server.

This tool performs ordinary TCP connect checks and Minecraft status pings. It does
not generate floods, spoof packets, or attempt to exhaust server resources.
"""
from __future__ import annotations

import csv
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from mcstatus import JavaServer
except ImportError:
    JavaServer = None  # type: ignore[assignment,misc]

APP_DIR = Path(__file__).resolve().parent
LOG_PATH = APP_DIR / "diagnostics.csv"
CSV_FIELDS = ["timestamp_utc", "test", "host", "port", "success", "latency_ms", "details"]
MAX_RUNS = 20
MIN_INTERVAL = 1.0


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_host(raw: str) -> str:
    host = raw.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if "://" in host:
        raise ValueError("Nhập hostname/IP, không nhập URL có http:// hoặc https://.")
    if not host:
        raise ValueError("Hostname/IP không được để trống.")
    return host


def log_result(test: str, host: str, port: int, success: bool,
               latency_ms: float | None, details: str) -> None:
    new_file = not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "timestamp_utc": timestamp(),
            "test": test,
            "host": host,
            "port": port,
            "success": "yes" if success else "no",
            "latency_ms": "" if latency_ms is None else f"{latency_ms:.2f}",
            "details": details.replace("\n", " ").replace("\r", " "),
        })


def tcp_check(host: str, port: int, family: int, timeout: float = 3.0) -> dict[str, Any]:
    label = "TCP/IPv4" if family == socket.AF_INET else "TCP/IPv6"
    try:
        infos = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return {"test": label, "ok": False, "latency": None,
                "details": f"Không tìm thấy địa chỉ phù hợp: {exc}"}

    errors: list[str] = []
    for af, socktype, proto, _canonname, sockaddr in infos:
        start = time.perf_counter()
        try:
            with socket.socket(af, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(sockaddr)
            ms = (time.perf_counter() - start) * 1000
            return {"test": label, "ok": True, "latency": ms,
                    "details": f"Kết nối TCP thành công tới {sockaddr[0]}:{port}"}
        except OSError as exc:
            errors.append(f"{sockaddr[0]}: {exc}")
    return {"test": label, "ok": False, "latency": None,
            "details": "; ".join(errors)[:500] or "Không kết nối được."}


def minecraft_status_check(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    if JavaServer is None:
        return {"test": "Minecraft Status (L7)", "ok": False, "latency": None,
                "details": "Thiếu thư viện mcstatus. Chạy: py -m pip install -r requirements.txt"}
    # mcstatus accepts bracketed IPv6 literals in host:port form.
    server_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    target = f"{server_host}:{port}"
    try:
        server = JavaServer.lookup(target, timeout=timeout)
        status = server.status()
        latency = float(status.latency) if status.latency is not None else None
        version = getattr(status.version, "name", "unknown")
        players = status.players
        online = getattr(players, "online", "?")
        maximum = getattr(players, "max", "?")
        details = f"Phản hồi status hợp lệ; version={version}; players={online}/{maximum}"
        return {"test": "Minecraft Status (L7)", "ok": True,
                "latency": latency, "details": details}
    except Exception as exc:  # include library/network errors in the diagnostic log
        return {"test": "Minecraft Status (L7)", "ok": False, "latency": None,
                "details": f"Status ping thất bại: {type(exc).__name__}: {exc}"[:500]}


def print_result(result: dict[str, Any], host: str, port: int) -> None:
    mark = "OK" if result["ok"] else "FAIL"
    latency = "—" if result["latency"] is None else f'{result["latency"]:.2f} ms'
    print(f'[{mark}] {result["test"]:<23} | {latency:>12} | {result["details"]}')
    log_result(result["test"], host, port, result["ok"], result["latency"], result["details"])


def get_int(prompt: str, default: int, minimum: int, maximum: int) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(f"Nhập số nguyên từ {minimum} đến {maximum}.")


def get_interval() -> float:
    while True:
        raw = input("Khoảng nghỉ giữa các lượt, giây [1.0]: ").strip()
        if not raw:
            return 1.0
        try:
            value = float(raw)
            if MIN_INTERVAL <= value <= 60:
                return value
        except ValueError:
            pass
        print("Khoảng nghỉ phải từ 1 đến 60 giây để giới hạn tải.")


def run_tests(mode: str, host: str, port: int) -> None:
    runs = get_int(f"Số lượt (1-{MAX_RUNS})", 5, 1, MAX_RUNS)
    interval = get_interval()
    timeout = 3.0
    print(f"\nĐích: {host}:{port} | lượt: {runs} | nghỉ: {interval:g}s | timeout: {timeout:g}s")
    print("Chỉ kiểm tra lưu lượng chẩn đoán thông thường; nhấn Ctrl+C để dừng.\n")
    funcs = {
        "4": [("TCP/IPv4", lambda: tcp_check(host, port, socket.AF_INET, timeout))],
        "6": [("TCP/IPv6", lambda: tcp_check(host, port, socket.AF_INET6, timeout))],
        "7": [("Minecraft Status (L7)", lambda: minecraft_status_check(host, port, timeout))],
        "all": [
            ("TCP/IPv4", lambda: tcp_check(host, port, socket.AF_INET, timeout)),
            ("TCP/IPv6", lambda: tcp_check(host, port, socket.AF_INET6, timeout)),
            ("Minecraft Status (L7)", lambda: minecraft_status_check(host, port, timeout)),
        ],
    }[mode]
    try:
        for i in range(runs):
            print(f"--- Lượt {i + 1}/{runs} | {timestamp()} ---")
            for _label, fn in funcs:
                print_result(fn(), host, port)
            if i + 1 < runs:
                time.sleep(interval)
        print(f"\nHoàn tất. Log CSV: {LOG_PATH}")
    except KeyboardInterrupt:
        print(f"\nĐã dừng theo yêu cầu. Log CSV: {LOG_PATH}")


def main() -> int:
    print("=" * 64)
    print(" Minecraft Paper/Spigot — Low-Rate Diagnostics")
    print(" Dùng cho máy chủ bạn sở hữu hoặc được ủy quyền kiểm thử")
    print("=" * 64)
    host = ""
    port = 25565
    while not host:
        try:
            host = normalize_host(input("Hostname/IP server: "))
        except ValueError as exc:
            print(exc)
    port = get_int("Port Minecraft", 25565, 1, 65535)

    while True:
        print("\nChọn kiểm tra:")
        print("  1. TCP IPv4 (kiểm tra kết nối L4)")
        print("  2. TCP IPv6 (kiểm tra khả năng kết nối qua IPv6; IPv6 không phải OSI L6)")
        print("  3. Minecraft Status/Ping (kiểm tra giao thức ứng dụng)")
        print("  4. Chạy bộ kiểm tra tổng hợp")
        print("  5. Đổi hostname/IP hoặc port")
        print("  0. Thoát")
        choice = input("Lựa chọn: ").strip()
        if choice in {"1", "2", "3", "4"}:
            mode = {"1": "4", "2": "6", "3": "7", "4": "all"}[choice]
            run_tests(mode, host, port)
        elif choice == "5":
            while True:
                try:
                    host = normalize_host(input("Hostname/IP mới: "))
                    break
                except ValueError as exc:
                    print(exc)
            port = get_int("Port Minecraft", port, 1, 65535)
        elif choice == "0":
            print("Đã thoát.")
            return 0
        else:
            print("Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, OSError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise SystemExit(1)
