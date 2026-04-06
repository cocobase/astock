import time
from loguru import logger
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from .base import BaseDataSource

class DataSourceManager:
    def __init__(self, retry_count: int = 2, timeout: int = 10):
        self.retry_count = retry_count
        self.timeout = timeout
        self.sources: Dict[str, BaseDataSource] = {}

    def register_source(self, source: BaseDataSource):
        """注册数据源"""
        self.sources[source.source_name] = source
        logger.info(f"注册数据源: {source.source_name}")

    def fetch_with_failover(self, market_priority: List[str], stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        """
        按优先级顺序调用数据源，支持失败重试和自动切换。
        """
        for source_name in market_priority:
            source = self.sources.get(source_name)
            if not source:
                logger.warning(f"数据源 {source_name} 未在注册列表中，跳过")
                continue

            for attempt in range(self.retry_count + 1):
                try:
                    logger.debug(f"尝试从 {source_name} 获取数据 (第 {attempt+1} 次尝试)")
                    data = source.fetch_daily_kline(stock_code, trade_date)
                    
                    if data is not None and not data.empty:
                        return data
                    else:
                        logger.warning(f"数据源 {source_name} 返回空数据 (第 {attempt+1} 次)")
                except Exception as e:
                    logger.error(f"数据源 {source_name} 调用异常: {e}")
                
                if attempt < self.retry_count:
                    time.sleep(1) # 重试间隔

            logger.error(f"数据源 {source_name} 在所有重试后均失败，切换至下一优先级")
        
        return None

    def fetch_historical_with_failover(self, market_priority: List[str], stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        批量获取历史日K数据，支持失败重试和自动切换。
        """
        for source_name in market_priority:
            source = self.sources.get(source_name)
            if not source:
                continue

            for attempt in range(self.retry_count + 1):
                try:
                    logger.debug(f"尝试从 {source_name} 获取历史数据 {stock_code} ({attempt+1}/{self.retry_count+1})")
                    data = source.fetch_historical_kline(stock_code, start_date, end_date)
                    
                    if data is not None and not data.empty:
                        return data
                except Exception as e:
                    logger.error(f"数据源 {source_name} 批量获取异常: {e}")
                
                if attempt < self.retry_count:
                    time.sleep(1)

            logger.error(f"数据源 {source_name} 历史获取在所有重试后均失败")
        
        return None
