from futu import OpenQuoteContext, RET_OK, KLType, AuType, Session
from datetime import datetime
import pandas as pd
from typing import Optional
from loguru import logger
from src.data_sources.base import BaseDataSource
from src.constants import KlineFields, AdjType

class FutuDataSource(BaseDataSource):
    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        self._host = host
        self._port = port
        self._quote_ctx = None
        self._source_name = "futu"

    @property
    def source_name(self) -> str:
        return self._source_name

    def _ensure_connected(self):
        if self._quote_ctx is None:
            try:
                self._quote_ctx = OpenQuoteContext(host=self._host, port=self._port)
                logger.info(f"成功连接至 FutuOpenD ({self._host}:{self._port})")
            except Exception as e:
                logger.error(f"连接 FutuOpenD 失败: {e}")
                self._quote_ctx = None

    def health_check(self) -> bool:
        self._ensure_connected()
        if self._quote_ctx:
            # 使用 extended unpacking 以兼容可能返回的多变量
            res = self._quote_ctx.get_global_state()
            if isinstance(res, tuple) and len(res) >= 2:
                ret, data = res[0], res[1]
                if ret == RET_OK:
                    return True
        return False

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        self._ensure_connected()
        if not self._quote_ctx:
            return None

        date_str = trade_date.strftime("%Y-%m-%d")
        
        # 富途 API 获取历史K线 (新版接口返回 3 个值: ret, data, page_req_key)
        # 参考 exam.py，使用 Session.ALL 并推荐使用枚举
        ret, data, page_req_key = self._quote_ctx.request_history_kline(
            code=stock_code,
            start=date_str,
            end=date_str,
            ktype=KLType.K_DAY,
            autype=AuType.QFQ, # 默认前复权
            session=Session.ALL
        )

        if ret != RET_OK:
            logger.error(f"富途数据源获取失败 ({stock_code} @ {date_str}): {data}")
            return None

        if data.empty:
            return None

        # 转换为标准字段格式
        df = pd.DataFrame()
        # 富途返回的 time_key 格式为 "YYYY-MM-DD HH:MM:SS"
        df[KlineFields.TRADE_DATE] = data['time_key'].apply(lambda x: x.split(' ')[0])
        df[KlineFields.STOCK_CODE] = data['code']
        df[KlineFields.OPEN] = data['open']
        df[KlineFields.HIGH] = data['high']
        df[KlineFields.LOW] = data['low']
        df[KlineFields.CLOSE] = data['close']
        df[KlineFields.VOLUME] = data['volume']
        df[KlineFields.AMOUNT] = data['turnover']
        df[KlineFields.ADJ_TYPE] = AdjType.QFQ.value
        df[KlineFields.SOURCE] = self.source_name
        df[KlineFields.FETCH_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df

    def close(self):
        if self._quote_ctx:
            self._quote_ctx.close()
            self._quote_ctx = None
            logger.info("已关闭富途 API 连接")
