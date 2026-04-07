import asyncio
import exchange_calendars as ecals
import pandas as pd
from datetime import datetime, timedelta
import pytz
from loguru import logger
from typing import List, Optional, Dict
from src.models import MarketStatus


class CalendarChecker:
    _instance = None
    _calendars = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CalendarChecker, cls).__new__(cls)
        return cls._instance

    def get_calendar(self, exchange_code: str):
        """获取并缓存交易所日历实例 (单例模式)"""
        if exchange_code not in self._calendars:
            try:
                self._calendars[exchange_code] = ecals.get_calendar(exchange_code)
                logger.info(f"成功加载日历: {exchange_code}")
            except Exception as e:
                logger.error(f"加载日历失败 {exchange_code}: {e}")
                return None
        return self._calendars[exchange_code]

    def is_trading_day(self, exchange_code: str, date: datetime) -> bool:
        """判断指定日期是否为该市场的交易日"""
        calendar = self.get_calendar(exchange_code)
        if not calendar:
            return date.weekday() < 5
        date_str = date.strftime("%Y-%m-%d")
        return calendar.is_session(date_str)

    def _fallback_previous_weekday(self, market_now: datetime) -> datetime:
        """兜底逻辑：回退到最近一个工作日"""
        candidate = market_now.replace(hour=0, minute=0, second=0, microsecond=0)
        while candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
        return candidate

    def get_market_trading_status(self, market_name: str, exchange_code: str, timezone_str: str) -> MarketStatus:
        """获取市场当前标准化状态模型"""
        market_tz = pytz.timezone(timezone_str)
        now_in_market = datetime.now(pytz.utc).astimezone(market_tz)
        today_str = now_in_market.strftime("%Y-%m-%d")
        calendar = self.get_calendar(exchange_code)

        if not calendar:
            is_trading_day_today = now_in_market.weekday() < 5
            last_trading_day = self._fallback_previous_weekday(now_in_market - timedelta(days=1))
            return MarketStatus(
                market_name=market_name,
                exchange_code=exchange_code,
                timezone=timezone_str,
                market_now=now_in_market.strftime("%Y-%m-%d %H:%M:%S%z"),
                market_date=today_str,
                is_trading_day_today=is_trading_day_today,
                is_current_session_closed=True,
                last_trading_day=last_trading_day.strftime("%Y-%m-%d"),
                calendar_source="fallback"
            )

        try:
            is_trading_day_today = calendar.is_session(today_str)
            if is_trading_day_today:
                session_close_utc = calendar.session_close(today_str)
                is_current_session_closed = now_in_market > session_close_utc.astimezone(market_tz)
                last_trading_day = today_str if is_current_session_closed else calendar.previous_session(today_str).strftime("%Y-%m-%d")
            else:
                is_current_session_closed = True
                last_trading_day = calendar.date_to_session(today_str, direction="previous").strftime("%Y-%m-%d")

            return MarketStatus(
                market_name=market_name,
                exchange_code=exchange_code,
                timezone=timezone_str,
                market_now=now_in_market.strftime("%Y-%m-%d %H:%M:%S%z"),
                market_date=today_str,
                is_trading_day_today=is_trading_day_today,
                is_current_session_closed=is_current_session_closed,
                last_trading_day=last_trading_day,
            )
        except Exception as e:
            logger.warning(f"获取市场状态失败 {exchange_code}: {e}")
            last_trading_day = self._fallback_previous_weekday(now_in_market - timedelta(days=1))
            return MarketStatus(
                market_name=market_name,
                exchange_code=exchange_code,
                timezone=timezone_str,
                market_now=now_in_market.strftime("%Y-%m-%d %H:%M:%S%z"),
                market_date=today_str,
                is_trading_day_today=now_in_market.weekday() < 5,
                is_current_session_closed=True,
                last_trading_day=last_trading_day.strftime("%Y-%m-%d"),
                calendar_source="fallback"
            )

    def get_all_market_statuses(self, market_configs: Dict[str, Dict]) -> Dict[str, MarketStatus]:
        """获取所有已配置市场的标准化状态模型"""
        result = {}
        for market_name, config in market_configs.items():
            status = self.get_market_trading_status(
                market_name, config.get("calendar"), config.get("timezone")
            )
            result[market_name] = status
        return result

    def get_recent_trading_days(self, exchange_code: str, days: int, end_date: Optional[datetime] = None) -> List[datetime]:
        """获取最近 N 个交易日列表"""
        calendar = self.get_calendar(exchange_code)
        if not calendar:
            result = []
            curr = end_date or datetime.now()
            while len(result) < days:
                if curr.weekday() < 5:
                    result.append(curr.replace(hour=0, minute=0, second=0, microsecond=0))
                curr -= timedelta(days=1)
            return sorted(result)

        if end_date:
            last_session_str = end_date.strftime("%Y-%m-%d")
            last_session = pd.Timestamp(last_session_str) if calendar.is_session(last_session_str) else calendar.date_to_session(last_session_str, direction="previous")
        else:
            today_str = datetime.now().strftime("%Y-%m-%d")
            last_session = pd.Timestamp(today_str) if calendar.is_session(today_str) else calendar.date_to_session(today_str, direction="previous")

        sessions = calendar.sessions_window(last_session, -days)
        return [s.to_pydatetime() for s in sessions]
