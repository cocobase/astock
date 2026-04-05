import exchange_calendars as ecals
import pandas as pd
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import pytz
from loguru import logger


@dataclass
class MarketTradingStatus:
    exchange_code: str
    timezone: str
    market_now: str
    market_date: str
    is_trading_day_today: bool
    is_current_session_closed: bool
    last_trading_day: str
    calendar_source: str = "exchange_calendars"

    def to_dict(self) -> dict:
        return asdict(self)


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
        """
        判断指定日期是否为该市场的交易日。
        :param exchange_code: 交易所代码 (如 XSHG, XHKG, XNYS)
        :param date: 目标日期 (datetime 对象)
        """
        calendar = self.get_calendar(exchange_code)
        if not calendar:
            # 兜底逻辑：排除周六日
            logger.warning(f"日历不可用，触发兜底判断逻辑 (排除周末)")
            return date.weekday() < 5
        
        # 转换为 UTC 零点进行判断 (exchange_calendars 的标准化要求)
        date_str = date.strftime("%Y-%m-%d")
        return calendar.is_session(date_str)

    def is_market_closed(self, exchange_code: str, trade_date: datetime, timezone_str: str) -> bool:
        """
        判断指定市场的指定交易日是否已经结束（收盘）。
        :param exchange_code: 交易所代码 (如 XSHG, XHKG, XNYS)
        :param trade_date: 目标交易日 (仅日期部分有效)
        :param timezone_str: 市场时区 (如 Asia/Shanghai)
        """
        calendar = self.get_calendar(exchange_code)
        if not calendar:
            # 兜底逻辑：默认已收盘 (防止配置错误导致流程卡死)
            return True
        
        # 获取该交易日的收盘时间 (返回的是 UTC 时间)
        try:
            session_close_utc = calendar.session_close(trade_date.strftime("%Y-%m-%d"))
            
            # 获取当前市场的当前时间
            market_tz = pytz.timezone(timezone_str)
            now_in_market = datetime.now(pytz.utc).astimezone(market_tz)
            
            # 将收盘时间转换为市场本地时间
            close_in_market = session_close_utc.astimezone(market_tz)
            
            # 比较：如果当前市场时间 > 收盘时间，说明已收盘
            return now_in_market > close_in_market
        except Exception as e:
            logger.warning(f"获取收盘时间失败 {exchange_code} @ {trade_date}: {e}")
            return True

    def _fallback_previous_weekday(self, market_now: datetime) -> datetime:
        """兜底逻辑：回退到最近一个工作日（不识别法定节假日）。"""
        candidate = market_now.replace(hour=0, minute=0, second=0, microsecond=0)
        while candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
        return candidate

    def get_market_trading_status(self, exchange_code: str, timezone_str: str) -> MarketTradingStatus:
        """
        获取市场当前状态：
        - 当前市场本地日期是否交易日
        - 当前日期交易时段是否已结束
        - 当前“最后一个交易日”日期

        规则：
        - 若今天是交易日且已收盘，最后一个交易日 = 今天
        - 若今天是交易日但未收盘，最后一个交易日 = 上一个交易日
        - 若今天不是交易日，最后一个交易日 = 上一个交易日
        """
        market_tz = pytz.timezone(timezone_str)
        now_in_market = datetime.now(pytz.utc).astimezone(market_tz)
        today_str = now_in_market.strftime("%Y-%m-%d")
        calendar = self.get_calendar(exchange_code)

        if not calendar:
            logger.warning(f"日历不可用，使用兜底逻辑推断市场状态: {exchange_code}")
            is_trading_day_today = now_in_market.weekday() < 5
            is_current_session_closed = True
            if is_trading_day_today:
                last_trading_day = now_in_market if is_current_session_closed else now_in_market - timedelta(days=1)
            else:
                last_trading_day = self._fallback_previous_weekday(now_in_market - timedelta(days=1))

            return MarketTradingStatus(
                exchange_code=exchange_code,
                timezone=timezone_str,
                market_now=now_in_market.strftime("%Y-%m-%d %H:%M:%S%z"),
                market_date=today_str,
                is_trading_day_today=is_trading_day_today,
                is_current_session_closed=is_current_session_closed,
                last_trading_day=last_trading_day.strftime("%Y-%m-%d"),
                calendar_source="fallback"
            )

        try:
            is_trading_day_today = calendar.is_session(today_str)

            if is_trading_day_today:
                session_close_utc = calendar.session_close(today_str)
                close_in_market = session_close_utc.astimezone(market_tz)
                is_current_session_closed = now_in_market > close_in_market

                if is_current_session_closed:
                    last_trading_day = today_str
                else:
                    last_trading_day = calendar.previous_session(today_str).strftime("%Y-%m-%d")
            else:
                is_current_session_closed = True
                last_trading_day = calendar.date_to_session(today_str, direction="previous").strftime("%Y-%m-%d")

            return MarketTradingStatus(
                exchange_code=exchange_code,
                timezone=timezone_str,
                market_now=now_in_market.strftime("%Y-%m-%d %H:%M:%S%z"),
                market_date=today_str,
                is_trading_day_today=is_trading_day_today,
                is_current_session_closed=is_current_session_closed,
                last_trading_day=last_trading_day,
            )
        except Exception as e:
            logger.warning(f"获取市场状态失败 {exchange_code}: {e}，使用兜底逻辑")
            last_trading_day = self._fallback_previous_weekday(now_in_market - timedelta(days=1))
            return MarketTradingStatus(
                exchange_code=exchange_code,
                timezone=timezone_str,
                market_now=now_in_market.strftime("%Y-%m-%d %H:%M:%S%z"),
                market_date=today_str,
                is_trading_day_today=now_in_market.weekday() < 5,
                is_current_session_closed=True,
                last_trading_day=last_trading_day.strftime("%Y-%m-%d"),
                calendar_source="fallback"
            )

    def get_last_trading_day(self, exchange_code: str, timezone_str: str) -> datetime:
        """获取当前市场最后一个交易日（未收盘则返回上一交易日）。"""
        status = self.get_market_trading_status(exchange_code, timezone_str)
        local_tz = pytz.timezone(timezone_str)
        return local_tz.localize(datetime.strptime(status.last_trading_day, "%Y-%m-%d"))

    def get_all_market_statuses(self, market_configs: dict) -> dict[str, dict]:
        """
        一次性获取多个市场的状态。

        :param market_configs: 配置格式示例
            {
                "A-Share": {"calendar": "XSHG", "timezone": "Asia/Shanghai"},
                "HK": {"calendar": "XHKG", "timezone": "Asia/Hong_Kong"},
                "US": {"calendar": "XNYS", "timezone": "America/New_York"},
            }
        :return: {market_name: status_dict}
        """
        result = {}
        for market_name, market_config in (market_configs or {}).items():
            exchange_code = market_config.get("calendar")
            timezone_str = market_config.get("timezone")
            if not exchange_code or not timezone_str:
                logger.warning(f"市场配置缺失 calendar/timezone，跳过: {market_name}")
                continue

            status = self.get_market_trading_status(exchange_code, timezone_str)
            result[market_name] = status.to_dict()
        return result

    def get_logical_trading_day(self, market_name: str, timezone_str: str) -> datetime:
        """兼容旧接口：返回当前市场最后一个交易日。"""
        return self.get_last_trading_day(market_name, timezone_str)
