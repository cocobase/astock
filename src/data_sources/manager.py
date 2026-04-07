import asyncio
from loguru import logger
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from .base import BaseDataSource


class DataSourceManager:
    def __init__(self, retry_count: int = 2, timeout: int = 10, request_interval: float = 0.5):
        self.retry_count = retry_count
        self.timeout = timeout
        self.request_interval = request_interval
        self.sources: Dict[str, BaseDataSource] = {}
        self._lock = asyncio.Lock()  # 确保频率控制

    def register_source(self, source: BaseDataSource):
        """注册数据源"""
        self.sources[source.source_name] = source
        logger.info(f"注册数据源: {source.source_name}")

    async def fetch_async_with_failover(self, market_priority: List[str], stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        """
        [Async] 按优先级顺序调用数据源，支持异步等待和频率控制。
        """
        for source_name in market_priority:
            source = self.sources.get(source_name)
            if not source:
                continue

            for attempt in range(self.retry_count + 1):
                try:
                    # 频率控制：使用 Lock 配合 asyncio.sleep
                    async with self._lock:
                        await asyncio.sleep(self.request_interval)
                    
                    logger.debug(f"尝试从 {source_name} 异步获取数据 {stock_code} (尝试 {attempt+1})")
                    
                    # 使用 asyncio.to_thread 包装同步阻塞调用
                    data = await asyncio.to_thread(source.fetch_daily_kline, stock_code, trade_date)
                    
                    if data is not None and not data.empty:
                        return data
                except Exception as e:
                    logger.error(f"数据源 {source_name} 异步获取异常: {e}")
                
                if attempt < self.retry_count:
                    await asyncio.sleep(1)

        return None

    async def fetch_historical_async_with_failover(self, market_priority: List[str], stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        [Async] 异步批量获取历史日K数据。
        """
        for source_name in market_priority:
            source = self.sources.get(source_name)
            if not source:
                continue

            for attempt in range(self.retry_count + 1):
                try:
                    async with self._lock:
                        await asyncio.sleep(self.request_interval)
                    
                    logger.debug(f"尝试从 {source_name} 异步历史获取 {stock_code} (尝试 {attempt+1})")
                    
                    data = await asyncio.to_thread(source.fetch_historical_kline, stock_code, start_date, end_date)
                    
                    if data is not None and not data.empty:
                        return data
                except Exception as e:
                    logger.error(f"数据源 {source_name} 异步历史获取异常: {e}")
                
                if attempt < self.retry_count:
                    await asyncio.sleep(1)

        return None

    # 保留同步版本以兼容旧代码（如有必要），或逐步废弃
    def fetch_with_failover(self, market_priority: List[str], stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        # 注意：在 asyncio 运行环境下，建议全面使用 async 版本
        return asyncio.run(self.fetch_async_with_failover(market_priority, stock_code, trade_date))

    def fetch_historical_with_failover(self, market_priority: List[str], stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        return asyncio.run(self.fetch_historical_async_with_failover(market_priority, stock_code, start_date, end_date))
