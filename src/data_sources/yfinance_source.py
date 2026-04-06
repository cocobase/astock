import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from src.data_sources.base import BaseDataSource
from src.constants import KlineFields, AdjType

class YFinanceDataSource(BaseDataSource):
    def __init__(self, proxy: Optional[str] = None):
        self._source_name = "yfinance"
        self._proxy = proxy
        self._session = None
        if self._proxy:
            self._session = requests.Session()
            self._session.proxies = {
                'http': self._proxy,
                'https': self._proxy,
            }

    @property
    def source_name(self) -> str:
        return self._source_name

    def health_check(self) -> bool:
        """yfinance 通常不需要鉴权，返回 True 即可"""
        return True

    def _convert_code(self, stock_code: str) -> str:
        """
        将代码转换为 yfinance 识别的格式，支持 SH.600519 或 600519.SH 等格式
        SH.600519 -> 600519.SS
        SZ.000001 -> 000001.SZ
        HK.00700  -> 0700.HK
        US.AAPL   -> AAPL
        """
        parts = stock_code.split('.')
        if len(parts) != 2:
            return stock_code
        
        p1, p2 = parts[0].upper(), parts[1].upper()
        if p1 in ["SH", "SZ", "HK", "US"]:
            market, code = p1, parts[1]
        elif p2 in ["SH", "SZ", "HK", "US"]:
            market, code = p2, parts[0]
        else:
            return stock_code

        if market == "SH":
            return f"{code}.SS"
        elif market == "SZ":
            return f"{code}.SZ"
        elif market == "HK":
            # 港股在 yfinance 中通常是 4 位代码 + .HK
            return f"{code[-4:]}.HK" if len(code) == 5 and code.startswith('0') else f"{code}.HK"
        elif market == "US":
            return code.replace('.', '-')
        return code

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        # yfinance 的 download 接口中 end 是不包含的，所以要取 trade_date + 1
        start_date_str = trade_date.strftime("%Y-%m-%d")
        end_date = trade_date + timedelta(days=1)
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        symbol = self._convert_code(stock_code)
        
        try:
            # yfinance 默认返回复权后的数据 (auto_adjust=True 会把 Close 变成 Adj Close)
            # 我们这里为了保持统一，使用 progress=False 且不打印信息
            # 使用 session 参数代替 proxy 参数以解决版本不兼容问题
            df = yf.download(
                symbol,
                start=start_date_str,
                end=end_date_str,
                session=self._session,
                progress=False,
                auto_adjust=False # 获取原始 OHLC + Adj Close
            )
            
            if df is None or df.empty:
                logger.warning(f"yfinance 未能获取到数据: {stock_code} ({symbol}) @ {start_date_str}")
                return None

            # 统一字段映射
            # yfinance 返回字段: Open, High, Low, Close, Adj Close, Volume
            result_df = pd.DataFrame()
            
            # 处理 MultiIndex 情况 (yfinance 某些版本对于单股票也会返回 MultiIndex)
            if isinstance(df.columns, pd.MultiIndex):
                # 如果是多索引，第一个级别通常是字段名
                df.columns = df.columns.get_level_values(0)

            result_df[KlineFields.TRADE_DATE] = [trade_date.strftime("%Y-%m-%d")]
            result_df[KlineFields.STOCK_CODE] = stock_code
            result_df[KlineFields.OPEN] = df["Open"].values
            result_df[KlineFields.HIGH] = df["High"].values
            result_df[KlineFields.LOW] = df["Low"].values
            # 如果是前复权，我们取 Adj Close 还是 Close？
            # 为了与其他源保持一致，这里逻辑根据项目需求定。
            # 通常 yf 的 Adj Close 是包含了分红拆股的。
            result_df[KlineFields.CLOSE] = df["Adj Close"].values if "Adj Close" in df.columns else df["Close"].values
            result_df[KlineFields.VOLUME] = df["Volume"].values
            # yfinance 不直接提供成交额 (Amount)，可以用成交量 * 收盘价估算，或者留空
            result_df[KlineFields.AMOUNT] = df["Volume"].values * df["Close"].values
            result_df[KlineFields.ADJ_TYPE] = AdjType.QFQ.value
            result_df[KlineFields.SOURCE] = self.source_name
            result_df[KlineFields.FETCH_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return result_df

        except Exception as e:
            logger.error(f"yfinance 获取数据异常 ({stock_code}): {e}")
            return None
