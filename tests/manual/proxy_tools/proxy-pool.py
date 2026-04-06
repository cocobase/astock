#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
proxy_pool_builder.py

功能：
1. 从公开来源抓取免费代理
2. 两阶段验证代理：
   - 阶段1：基础连通性验证（httpbin）
   - 阶段2：财经数据目标验证（模拟 AkShare 场景）
3. 记录代理长期状态：
   - success_rate      成功率
   - avg_latency_ms    平均延迟
   - last_success_time 最近成功时间
   - consecutive_failures 连续失败次数
4. 导出：
   - 当前可用代理 working_proxies.txt
   - 当前可用详细信息 working_proxies.json
   - 完整状态库 proxy_state.json

依赖：
    pip install requests

运行：
    python proxy_pool_builder.py
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import statistics
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

import requests


# =========================
# 配置区
# =========================

FETCH_TIMEOUT = 10
TEST_TIMEOUT = 8
MAX_WORKERS = 50

STATE_FILE = "proxy_state.json"
WORKING_JSON_FILE = "working_proxies.json"
WORKING_TXT_FILE = "working_proxies.txt"

TEST_URL_STAGE_1 = "https://httpbin.org/ip"

# 阶段2：财经数据场景验证
# 这里不是“调用 akshare 库”，而是验证代理能否访问财经数据目标。
# 你可以替换为你在 AkShare 实际使用中最常碰到的上游站点。
FINANCE_TEST_TARGETS = [
    {
        "name": "eastmoney_quote_api",
        "url": "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600000&fields=f57,f58",
        "expected_keywords": ["f57", "f58"],
    },
    {
        "name": "sina_finance_basic",
        "url": "https://hq.sinajs.cn/list=sh600000",
        "expected_keywords": ["var hq_str_sh600000"],
    },
]

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=https&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/https.txt",
]

IP_PORT_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b")


# =========================
# 数据结构
# =========================

@dataclass
class ProxyMetrics:
    proxy: str
    total_checks: int = 0
    successful_checks: int = 0
    success_rate: float = 0.0

    latency_history_ms: List[int] = field(default_factory=list)
    avg_latency_ms: Optional[float] = None
    latest_latency_ms: Optional[int] = None

    last_success_time: Optional[str] = None
    consecutive_failures: int = 0

    stage1_ok: bool = False
    stage2_ok: bool = False
    last_origin_ip: Optional[str] = None
    last_finance_target: Optional[str] = None
    last_error: Optional[str] = None

    def update_after_check(
        self,
        success: bool,
        latency_ms: Optional[int],
        stage1_ok: bool,
        stage2_ok: bool,
        origin_ip: Optional[str],
        finance_target: Optional[str],
        error: Optional[str],
    ) -> None:
        self.total_checks += 1
        self.stage1_ok = stage1_ok
        self.stage2_ok = stage2_ok
        self.last_origin_ip = origin_ip
        self.last_finance_target = finance_target
        self.last_error = error

        if success:
            self.successful_checks += 1
            self.consecutive_failures = 0
            self.last_success_time = utc_now_iso()
            if latency_ms is not None:
                self.latest_latency_ms = latency_ms
                self.latency_history_ms.append(latency_ms)
                # 控制历史长度，避免状态文件无限膨胀
                self.latency_history_ms = self.latency_history_ms[-20:]
                self.avg_latency_ms = round(statistics.mean(self.latency_history_ms), 2)
        else:
            self.consecutive_failures += 1

        self.success_rate = round(self.successful_checks / self.total_checks, 4) if self.total_checks else 0.0


@dataclass
class CheckResult:
    proxy: str
    success: bool
    latency_ms: Optional[int]
    stage1_ok: bool
    stage2_ok: bool
    origin_ip: Optional[str]
    finance_target: Optional[str]
    error: Optional[str]


# =========================
# 工具函数
# =========================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> Dict[str, ProxyMetrics]:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    state: Dict[str, ProxyMetrics] = {}
    for proxy, item in raw.items():
        state[proxy] = ProxyMetrics(**item)
    return state


def save_state(state: Dict[str, ProxyMetrics]) -> None:
    data = {proxy: asdict(metrics) for proxy, metrics in state.items()}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_valid_ip_port(proxy: str) -> bool:
    try:
        host, port_str = proxy.split(":")
        parts = host.split(".")
        if len(parts) != 4:
            return False
        if not all(0 <= int(x) <= 255 for x in parts):
            return False
        port = int(port_str)
        return 1 <= port <= 65535
    except Exception:
        return False


def fetch_source(url: str) -> str:
    resp = requests.get(url, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def extract_proxies(text: str) -> Set[str]:
    found = set(IP_PORT_PATTERN.findall(text))
    return {p.strip() for p in found if is_valid_ip_port(p)}


def collect_proxies() -> List[str]:
    all_proxies: Set[str] = set()

    for url in PROXY_SOURCES:
        try:
            print(f"[+] 拉取来源: {url}")
            text = fetch_source(url)
            proxies = extract_proxies(text)
            print(f"    提取到 {len(proxies)} 个代理")
            all_proxies.update(proxies)
        except Exception as e:
            print(f"[!] 来源失败: {url} -> {e}")

    result = sorted(all_proxies)
    print(f"[+] 去重后代理总数: {len(result)}")
    return result


def build_requests_proxy(proxy: str) -> Dict[str, str]:
    # 免费代理大多以 HTTP CONNECT 方式提供
    return {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }


# =========================
# 两阶段验证
# =========================

def stage1_basic_connectivity(proxy: str) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    阶段1：验证基础连通性与出口 IP
    返回：
        ok, latency_ms, origin_ip, error
    """
    proxies = build_requests_proxy(proxy)
    start = time.perf_counter()

    try:
        resp = requests.get(TEST_URL_STAGE_1, proxies=proxies, timeout=TEST_TIMEOUT)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code != 200:
            return False, latency_ms, None, f"stage1 status={resp.status_code}"

        data = resp.json()
        origin_ip = data.get("origin")
        if not origin_ip:
            return False, latency_ms, None, "stage1 missing origin_ip"

        return True, latency_ms, origin_ip, None
    except Exception as e:
        return False, None, None, f"stage1 exception={type(e).__name__}: {e}"


def stage2_finance_validation(proxy: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    阶段2：财经数据链路验证
    只要 FINANCE_TEST_TARGETS 中任意一个目标验证通过，即视为通过。
    返回：
        ok, target_name, error
    """
    proxies = build_requests_proxy(proxy)

    for target in FINANCE_TEST_TARGETS:
        name = target["name"]
        url = target["url"]
        expected_keywords = target.get("expected_keywords", [])

        try:
            resp = requests.get(
                url,
                proxies=proxies,
                timeout=TEST_TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://quote.eastmoney.com/",
                },
            )

            if resp.status_code != 200:
                continue

            text = resp.text
            if all(keyword in text for keyword in expected_keywords):
                return True, name, None

        except Exception:
            continue

    return False, None, "stage2 finance target check failed"


def test_one_proxy(proxy: str) -> CheckResult:
    stage1_ok, latency_ms, origin_ip, err1 = stage1_basic_connectivity(proxy)
    if not stage1_ok:
        return CheckResult(
            proxy=proxy,
            success=False,
            latency_ms=latency_ms,
            stage1_ok=False,
            stage2_ok=False,
            origin_ip=origin_ip,
            finance_target=None,
            error=err1,
        )

    stage2_ok, finance_target, err2 = stage2_finance_validation(proxy)
    if not stage2_ok:
        return CheckResult(
            proxy=proxy,
            success=False,
            latency_ms=latency_ms,
            stage1_ok=True,
            stage2_ok=False,
            origin_ip=origin_ip,
            finance_target=None,
            error=err2,
        )

    return CheckResult(
        proxy=proxy,
        success=True,
        latency_ms=latency_ms,
        stage1_ok=True,
        stage2_ok=True,
        origin_ip=origin_ip,
        finance_target=finance_target,
        error=None,
    )


# =========================
# 评分与筛选
# =========================

def score_proxy(metrics: ProxyMetrics) -> float:
    """
    简单综合评分：
    - 成功率越高越好
    - 平均延迟越低越好
    - 连续失败越少越好
    - 最近成功时间这里只做展示，不直接折算分数
    """
    success_score = metrics.success_rate * 100

    if metrics.avg_latency_ms is None:
        latency_score = 0
    else:
        # 延迟越低越高分，做一个温和衰减
        latency_score = max(0, 40 - metrics.avg_latency_ms / 50)

    failure_penalty = min(metrics.consecutive_failures * 8, 40)

    total = success_score + latency_score - failure_penalty
    return round(total, 2)


def should_keep_as_working(metrics: ProxyMetrics) -> bool:
    """
    当前可用代理的最低门槛：
    - 最近一次两阶段验证都通过
    - 成功率 >= 0.3
    - 连续失败次数 <= 2
    """
    return (
        metrics.stage1_ok
        and metrics.stage2_ok
        and metrics.success_rate >= 0.3
        and metrics.consecutive_failures <= 2
    )


# =========================
# 主流程
# =========================

def test_proxies_and_update_state(proxies: List[str], state: Dict[str, ProxyMetrics]) -> Dict[str, ProxyMetrics]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(test_one_proxy, proxy): proxy for proxy in proxies}

        for idx, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
            proxy = future_map[future]

            if proxy not in state:
                state[proxy] = ProxyMetrics(proxy=proxy)

            try:
                result = future.result()
            except Exception as e:
                result = CheckResult(
                    proxy=proxy,
                    success=False,
                    latency_ms=None,
                    stage1_ok=False,
                    stage2_ok=False,
                    origin_ip=None,
                    finance_target=None,
                    error=f"unexpected exception={type(e).__name__}: {e}",
                )

            state[proxy].update_after_check(
                success=result.success,
                latency_ms=result.latency_ms,
                stage1_ok=result.stage1_ok,
                stage2_ok=result.stage2_ok,
                origin_ip=result.origin_ip,
                finance_target=result.finance_target,
                error=result.error,
            )

            status = "OK" if result.success else "NO"
            print(
                f"[{status}] {proxy:<21} "
                f"stage1={result.stage1_ok} "
                f"stage2={result.stage2_ok} "
                f"latency={result.latency_ms} "
                f"err={result.error}"
            )

            if idx % 50 == 0:
                ok_count = sum(1 for m in state.values() if should_keep_as_working(m))
                print(f"[...] 已测试 {idx} 个代理，当前合格 {ok_count} 个")

    return state


def export_working_proxies(state: Dict[str, ProxyMetrics]) -> None:
    working = [m for m in state.values() if should_keep_as_working(m)]
    working.sort(
        key=lambda m: (
            -m.success_rate,
            m.avg_latency_ms if m.avg_latency_ms is not None else 999999,
            m.consecutive_failures,
        )
    )

    working_json = []
    for m in working:
        item = asdict(m)
        item["score"] = score_proxy(m)
        working_json.append(item)

    with open(WORKING_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(working_json, f, ensure_ascii=False, indent=2)

    with open(WORKING_TXT_FILE, "w", encoding="utf-8") as f:
        for m in working:
            f.write(f"{m.proxy}\n")

    print(f"[+] 当前可用代理数: {len(working)}")
    print(f"[+] 已导出: {WORKING_JSON_FILE}")
    print(f"[+] 已导出: {WORKING_TXT_FILE}")


def print_top_proxies(state: Dict[str, ProxyMetrics], top_n: int = 20) -> None:
    ranked = list(state.values())
    ranked.sort(key=lambda m: score_proxy(m), reverse=True)

    print("\n=== TOP PROXIES ===")
    for m in ranked[:top_n]:
        print(
            f"{m.proxy:<21} "
            f"score={score_proxy(m):>6} "
            f"success_rate={m.success_rate:>5} "
            f"avg_latency={str(m.avg_latency_ms):>8} "
            f"last_success={str(m.last_success_time):<30} "
            f"consecutive_failures={m.consecutive_failures}"
        )


def main() -> None:
    print("[*] 加载历史状态...")
    state = load_state()
    print(f"[+] 已加载历史代理状态数: {len(state)}")

    print("[*] 收集代理...")
    fresh_proxies = collect_proxies()

    # 可以把历史中最近跑过的代理也继续带上，避免只盯新代理
    all_proxies = sorted(set(fresh_proxies) | set(state.keys()))
    print(f"[+] 本次准备测试代理总数: {len(all_proxies)}")

    print("[*] 开始两阶段验证...")
    state = test_proxies_and_update_state(all_proxies, state)

    print("[*] 保存状态库...")
    save_state(state)

    print("[*] 导出当前可用代理...")
    export_working_proxies(state)

    print_top_proxies(state, top_n=20)


if __name__ == "__main__":
    main()
