from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd

@dataclass(frozen=True)
class KlineData:
    """标准日K线数据模型"""
    trade_date: str           # YYYY-MM-DD
    stock_code: str          # 原始代码
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: Optional[float] = None
    adj_type: str = "qfq"    # qfq, hfq, none
    source: str = ""         # 数据源名称
    fetch_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trade_date": self.trade_date,
            "stock_code": self.stock_code,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "adj_type": self.adj_type,
            "source": self.source,
            "fetch_time": self.fetch_time.strftime("%Y-%m-%d %H:%M:%S")
        }

    @classmethod
    def from_row(cls, row: pd.Series) -> 'KlineData':
        """从 pandas 行对象创建"""
        return cls(
            trade_date=str(row['trade_date']),
            stock_code=str(row['stock_code']),
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=float(row['volume']),
            amount=float(row.get('amount', 0)),
            adj_type=str(row.get('adj_type', 'qfq')),
            source=str(row.get('source', '')),
            fetch_time=datetime.now()
        )
