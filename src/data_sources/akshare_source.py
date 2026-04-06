import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Optional
from loguru import logger
from src.data_sources.base import BaseDataSource
from src.constants import KlineFields, AdjType

class AkshareDataSource(BaseDataSource):
    def __init__(self):
        self._source_name = "akshare"

    @property
    def source_name(self) -> str:
        return self._source_name

    def health_check(self) -> bool:
        """AKShare 通常不需要鉴权，返回 True 即可"""
        return True

    def _convert_code(self, stock_code: str) -> tuple[str, str]:
        """
        将代码转换为 AKShare 识别的格式
        支持 SH.600519 或 600519.SH 等格式
        """
        parts = stock_code.split('.')
        if len(parts) != 2:
            return stock_code, "Unknown"
        
        p1, p2 = parts[0].upper(), parts[1].upper()
        if p1 in ["SH", "SZ", "HK", "US"]:
            market, code = p1, parts[1]
        elif p2 in ["SH", "SZ", "HK", "US"]:
            market, code = p2, parts[0]
        else:
            return stock_code, "Unknown"

        if market in ["SH", "SZ"]:
            return code, "A-Share"
        elif market == "HK":
            return code, "HK"
        elif market == "US":
            return code, "US"
        return code, "Unknown"

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        date_str = trade_date.strftime("%Y%m%d")
        symbol, market = self._convert_code(stock_code)
        
        try:
            df = None
            if market == "A-Share":
                # A 股获取
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=date_str,
                    end_date=date_str,
                    adjust="qfq"
                )
            elif market == "HK":
                # 港股获取
                df = ak.stock_hk_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=date_str,
                    end_date=date_str,
                    adjust="qfq"
                )
            elif market == "US":
                # 美股获取
                df = ak.stock_us_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=date_str,
                    end_date=date_str,
                    adjust="qfq"
                )
            
            if df is None or df.empty:
                logger.warning(f"AKShare 未能获取到数据: {stock_code} @ {trade_date.strftime('%Y-%m-%d')}")
                return None

            # 统一字段映射
            # AKShare 返回字段: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
            result_df = pd.DataFrame()
            result_df[KlineFields.TRADE_DATE] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
            result_df[KlineFields.STOCK_CODE] = stock_code
            result_df[KlineFields.OPEN] = df["开盘"]
            result_df[KlineFields.HIGH] = df["最高"]
            result_df[KlineFields.LOW] = df["最低"]
            result_df[KlineFields.CLOSE] = df["收盘"]
            result_df[KlineFields.VOLUME] = df["成交量"]
            result_df[KlineFields.AMOUNT] = df["成交额"]
            result_df[KlineFields.ADJ_TYPE] = AdjType.QFQ.value
            result_df[KlineFields.SOURCE] = self.source_name
            result_df[KlineFields.FETCH_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return result_df

        except Exception as e:
            logger.error(f"AKShare 获取数据异常 ({stock_code}): {e}")
            return None
