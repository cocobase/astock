import sys
import os
import time
import threading
from datetime import datetime
from typing import List, Optional
import pandas as pd

# 将项目根目录添加到 python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_sources.akshare_source import AkshareDataSource

class AkshareContinuousTester:
    def __init__(self, stock_codes: List[str], trade_date: datetime, proxy_pool: List[str] = None):
        self.source = AkshareDataSource()
        self.stock_codes = stock_codes
        self.trade_date = trade_date
        self.processed_count = 0
        self.consecutive_failures = 0
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 代理池设置
        self.proxy_pool = proxy_pool or []
        self.proxy_index = 0

    def _get_next_proxy(self) -> Optional[str]:
        if not self.proxy_pool:
            return None
        proxy = self.proxy_pool[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_pool)
        return proxy

    def _fetch_with_proxy(self, code: str) -> Optional[pd.DataFrame]:
        proxy = self._get_next_proxy()
        if not proxy:
            print(f"  [跳过] 没有可用代理池。")
            return None
        
        print(f"  [代理重试] 正在尝试使用代理: {proxy}")
        
        # 备份当前环境
        old_http = os.environ.get('HTTP_PROXY')
        old_https = os.environ.get('HTTPS_PROXY')
        
        # 设置代理环境变量 (akshare 使用的 requests 会自动识别)
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy
        
        try:
            return self.source.fetch_daily_kline(code, self.trade_date)
        finally:
            # 还原环境变量
            if old_http: os.environ['HTTP_PROXY'] = old_http
            else: os.environ.pop('HTTP_PROXY', None)
            
            if old_https: os.environ['HTTPS_PROXY'] = old_https
            else: os.environ.pop('HTTPS_PROXY', None)

    def fetch_task(self):
        print(f"线程启动: 开始连续获取 {len(self.stock_codes)} 个股票数据 (代理池大小: {len(self.proxy_pool)})")
        
        for code in self.stock_codes:
            if self.stop_event.is_set():
                break

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在请求: {code}")
            
            df = None
            try:
                # 1. 尝试直接获取
                df = self.source.fetch_daily_kline(code, self.trade_date)
                
                # 2. 如果失败且有代理池，尝试使用代理
                if (df is None or df.empty) and self.proxy_pool:
                    print(f"  警告: 首次请求 {code} 失败，准备使用代理重试...")
                    df = self._fetch_with_proxy(code)
                
                with self._lock:
                    self.processed_count += 1
                
                if df is not None and not df.empty:
                    print(f"  成功获取 {code} 数据，共 {len(df)} 行")
                    self.consecutive_failures = 0
                else:
                    self.consecutive_failures += 1
                    print(f"  错误: 无法通过任何方式获取 {code} 数据 (连续失败次数: {self.consecutive_failures})")
                
            except Exception as e:
                # 处理未被 source 捕获的异常
                self.consecutive_failures += 1
                print(f"  异常: 处理 {code} 时发生严重错误: {e} (连续失败次数: {self.consecutive_failures})")

            if self.consecutive_failures >= 3:
                print("!!! 连续 3 次无法获得数据，触发熔断，退出线程...")
                self.stop_event.set()
                break

            # 间隔10秒
            time.sleep(10)

        print(f"线程任务完成。")

    def run(self):
        thread = threading.Thread(target=self.fetch_task)
        thread.start()
        return thread

if __name__ == "__main__":
    # 测试代码
    test_codes = ["SH.600036", "SH.600519", "SZ.300750", "HK.00700"]
    test_date = datetime(2026, 3, 30)
    
    # 定义代理池 (示例代理)
    proxies = [
        "http://147.161.239.240:8800"
    ]
    
    tester = AkshareContinuousTester(test_codes, test_date, proxy_pool=proxies)
    test_thread = tester.run()
    
    try:
        while test_thread.is_alive():
            test_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\n用户手动停止。")
        tester.stop_event.set()
        test_thread.join()

    print(f"--- 测试报告 ---")
    print(f"累计处理请求 (含重试): {tester.processed_count}")
    print(f"最终完成状态: {'异常终止' if tester.consecutive_failures >= 3 else '正常结束'}")
