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

    def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """批量获取历史K线数据"""
        symbol = self._convert_code(stock_code)
        start_str = start_date.strftime("%Y-%m-%d")
        # yfinance 的 end 是不包含的
        end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            df = yf.download(
                symbol,
                start=start_str,
                end=end_str,
                session=self._session,
                progress=False,
                auto_adjust=False
            )
            
            if df is None or df.empty:
                return None

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            result_df = pd.DataFrame()
            result_df[KlineFields.TRADE_DATE] = df.index.strftime("%Y-%m-%d")
            result_df[KlineFields.STOCK_CODE] = stock_code
            result_df[KlineFields.OPEN] = df["Open"].values
            result_df[KlineFields.HIGH] = df["High"].values
            result_df[KlineFields.LOW] = df["Low"].values
            result_df[KlineFields.CLOSE] = df["Adj Close"].values if "Adj Close" in df.columns else df["Close"].values
            result_df[KlineFields.VOLUME] = df["Volume"].values
            result_df[KlineFields.AMOUNT] = df["Volume"].values * df["Close"].values
            result_df[KlineFields.ADJ_TYPE] = AdjType.QFQ.value
            result_df[KlineFields.SOURCE] = self.source_name
            result_df[KlineFields.FETCH_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return result_df

        except Exception as e:
            logger.error(f"yfinance 批量获取异常 ({stock_code}): {e}")
            return None

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        """复用批量获取接口"""
        return self.fetch_historical_kline(stock_code, trade_date, trade_date)
