from unittest.mock import patch

from src.trading_calendar.checker import CalendarChecker, MarketTradingStatus


class DummySessionPoint:
    def __init__(self, value: str):
        self.value = value

    def strftime(self, fmt: str) -> str:
        return self.value


class DummyClose:
    def __init__(self, dt):
        self._dt = dt

    def astimezone(self, tz):
        return self._dt.astimezone(tz)


class DummyCalendar:
    def __init__(self, *, is_session=True, previous_session_str="2026-04-02", date_to_session_str="2026-04-02", session_close_dt=None):
        self._is_session = is_session
        self._previous_session_str = previous_session_str
        self._date_to_session_str = date_to_session_str
        self._session_close_dt = session_close_dt

    def is_session(self, date_str):
        return self._is_session

    def session_close(self, date_str):
        return DummyClose(self._session_close_dt)

    def previous_session(self, date_str):
        return DummySessionPoint(self._previous_session_str)

    def date_to_session(self, date_str, direction="previous"):
        return DummySessionPoint(self._date_to_session_str)


class FixedDateTime:
    @classmethod
    def now(cls, tz=None):
        import pytz
        base = pytz.utc.localize(__import__("datetime").datetime(2026, 4, 3, 14, 0, 0))
        return base if tz is None else base.astimezone(tz)

    @classmethod
    def strptime(cls, *args, **kwargs):
        from datetime import datetime
        return datetime.strptime(*args, **kwargs)


def test_market_trading_status_closed_session_returns_today():
    import pytz
    checker = CalendarChecker()
    close_dt = pytz.timezone("Asia/Shanghai").localize(__import__("datetime").datetime(2026, 4, 3, 15, 0, 0))
    cal = DummyCalendar(is_session=True, session_close_dt=close_dt)

    with patch.object(CalendarChecker, "get_calendar", return_value=cal), patch("src.trading_calendar.checker.datetime", FixedDateTime):
        status = checker.get_market_trading_status("XSHG", "Asia/Shanghai")

    assert isinstance(status, MarketTradingStatus)
    assert status.is_trading_day_today is True
    assert status.is_current_session_closed is True
    assert status.last_trading_day == "2026-04-03"


def test_market_trading_status_open_session_returns_previous_session():
    import pytz
    checker = CalendarChecker()
    close_dt = pytz.timezone("Asia/Shanghai").localize(__import__("datetime").datetime(2026, 4, 3, 23, 0, 0))
    cal = DummyCalendar(is_session=True, previous_session_str="2026-04-02", session_close_dt=close_dt)

    with patch.object(CalendarChecker, "get_calendar", return_value=cal), patch("src.trading_calendar.checker.datetime", FixedDateTime):
        status = checker.get_market_trading_status("XSHG", "Asia/Shanghai")

    assert status.is_trading_day_today is True
    assert status.is_current_session_closed is False
    assert status.last_trading_day == "2026-04-02"


def test_market_trading_status_non_trading_day_returns_previous_session():
    checker = CalendarChecker()
    cal = DummyCalendar(is_session=False, date_to_session_str="2026-04-02", session_close_dt=None)

    with patch.object(CalendarChecker, "get_calendar", return_value=cal), patch("src.trading_calendar.checker.datetime", FixedDateTime):
        status = checker.get_market_trading_status("XNYS", "America/New_York")

    assert status.is_trading_day_today is False
    assert status.is_current_session_closed is True
    assert status.last_trading_day == "2026-04-02"


def test_get_all_market_statuses_returns_all_markets():
    checker = CalendarChecker()

    def fake_status(exchange_code, timezone_str):
        return MarketTradingStatus(
            exchange_code=exchange_code,
            timezone=timezone_str,
            market_now="2026-04-03 22:00:00+0800",
            market_date="2026-04-03",
            is_trading_day_today=True,
            is_current_session_closed=True,
            last_trading_day="2026-04-03",
        )

    market_configs = {
        "A-Share": {"calendar": "XSHG", "timezone": "Asia/Shanghai"},
        "HK": {"calendar": "XHKG", "timezone": "Asia/Hong_Kong"},
        "BROKEN": {"calendar": "", "timezone": "Asia/Shanghai"},
    }

    with patch.object(CalendarChecker, "get_market_trading_status", side_effect=fake_status):
        result = checker.get_all_market_statuses(market_configs)

    assert set(result.keys()) == {"A-Share", "HK"}
    assert result["A-Share"]["exchange_code"] == "XSHG"
    assert result["HK"]["timezone"] == "Asia/Hong_Kong"
