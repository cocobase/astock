from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
from typing import Optional

class BaseDataSource(ABC):
    @abstractmethod
    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        """获取指定标的在指定日期的收盘日K数据"""
        pass

    @abstractmethod
    def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """获取指定时间段的历史日K线数据"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """检查数据源连通性/权限"""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称"""
        pass

class StubDataSource(BaseDataSource):
    """
    用于阶段 0 测试的桩数据源。
    可以模拟成功、失败或超时。
    """
    def __init__(self, name: str, behavior: str = "success"):
        self._name = name
        self.behavior = behavior # success, failure, timeout

    @property
    def source_name(self) -> str:
        return self._name

    def health_check(self) -> bool:
        return True

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        if self.behavior == "success":
            # 返回一行模拟数据
            return pd.DataFrame([{
                "trade_date": trade_date.strftime("%Y-%m-%d"),
                "stock_code": stock_code,
                "open": 100.0,
                "high": 110.0,
                "low": 90.0,
                "close": 105.0,
                "volume": 1000000,
                "amount": 105000000,
                "adj_type": "qfq",
                "source": self.source_name,
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
                    "volume": 1000000, "amount": 105000000, "adj_type": "qfq",
                    "source": self.source_name,
                    "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            return pd.DataFrame(rows)
        elif self.behavior == "failure":
            raise Exception(f"Stub source '{self.source_name}' simulated historical failure.")
        return None
