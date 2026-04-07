from abc import ABC, abstractmethod
from typing import List, Optional, Union
from datetime import datetime, timedelta
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


class StubDataSource(BaseDataSource):
    """
    用于测试的桩数据源。
    可以模拟成功、失败或空数据。
    """
    def __init__(self, source_name: str, behavior: str = "success"):
        super().__init__(source_name)
        self.behavior = behavior  # success, failure, empty

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        if self.behavior == "success":
            return pd.DataFrame([{
                "trade_date": trade_date.strftime("%Y-%m-%d"),
                "stock_code": stock_code,
                "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0,
                "volume": 1000000, "source": self.source_name,
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
        elif self.behavior == "failure":
            raise Exception(f"Stub source '{self.source_name}' simulated failure.")
        return None

    def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        if self.behavior == "success":
            # 模拟返回 3 条数据
            dates = [start_date, start_date + (end_date - start_date) / 2, end_date]
            rows = []
            for d in dates:
                rows.append({
                    "trade_date": d.strftime("%Y-%m-%d"),
                    "stock_code": stock_code,
                    "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0,
                    "volume": 1000000, "source": self.source_name,
                    "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            return pd.DataFrame(rows)
        elif self.behavior == "failure":
            raise Exception(f"Stub source '{self.source_name}' simulated historical failure.")
        return None
