from abc import ABC, abstractmethod
from typing import List, Optional, Union
from datetime import datetime
import pandas as pd
from src.models import KlineData


class BaseDataSource(ABC):
    """
    数据源抽象基类。
    Phase 3: 接口定义将逐步迁移至返回 List[KlineData]
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        """获取指定标的、指定日期的日K线数据 (同步)"""
        pass

    @abstractmethod
    def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """批量获取指定标的的历史日K线数据 (同步)"""
        pass

    def close(self):
        """可选的资源清理操作"""
        pass
