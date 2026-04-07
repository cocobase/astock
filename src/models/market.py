from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass(frozen=True)
class MarketStatus:
    """标准化市场状态模型"""
    market_name: str
    exchange_code: str
    timezone: str
    market_now: str
    market_date: str
    is_trading_day_today: bool
    is_current_session_closed: bool
    last_trading_day: str
    calendar_source: str = "exchange_calendars"

    def __post_init__(self):
        # 基本校验（可选）
        if not self.market_name:
            raise ValueError("市场名称不能为空")
        if not self.exchange_code:
            raise ValueError("交易所编码不能为空")
