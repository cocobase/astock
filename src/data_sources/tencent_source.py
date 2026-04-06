import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from loguru import logger
from src.data_sources.base import BaseDataSource
from src.constants import KlineFields, AdjType

class TencentDataSource(BaseDataSource):
    """
    腾讯财经数据源，提供 A 股、港股、美股的历史 K 线和实时行情。
    支持前复权、后复权和不复权。
    """
    def __init__(self, proxy: Optional[str] = None):
        self._source_name = "tencent"
        self._snapshot_url = "https://qt.gtimg.cn/q="
        self._hist_url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        self._us_hist_url = "https://web.ifzq.gtimg.cn/appstock/app/usfqkline/get"
        self._hk_hist_url = "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get"
        self._proxy = proxy
        self._session = requests.Session()
        if self._proxy:
            self._session.proxies = {
                'http': self._proxy,
                'https': self._proxy,
            }
        
        # 常用美股后缀映射表 (Symbol -> Suffix)
        self._us_suffix_map = {
            "AAPL": ".OQ", "NVDA": ".OQ", "MSFT": ".OQ", "GOOGL": ".OQ", "AMZN": ".OQ",
            "META": ".OQ", "AVGO": ".OQ", "TSLA": ".OQ", "NFLX": ".OQ", "COST": ".OQ",
            "JPM": ".N", "V": ".N", "MA": ".N", "WMT": ".N", "PG": ".N", "XOM": ".N",
            "DIS": ".N", "KO": ".N", "NKE": ".N", "BA": ".N", "GS": ".N"
        }

    @property
    def source_name(self) -> str:
        return self._source_name

    def health_check(self) -> bool:
        """检查腾讯接口连通性"""
        try:
            # 使用上证指数代码进行健康检查
            response = self._session.get(f"{self._snapshot_url}sh000001", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Tencent DataSource health check failed: {e}")
            return False

    def _transform_symbol(self, stock_code: str, for_hist: bool = False) -> str:
        """转换代码格式，支持 SH.600519 或 600519.SH 等格式"""
        parts = stock_code.split('.')
        if len(parts) != 2:
            return stock_code.lower()
        
        p1, p2 = parts[0].upper(), parts[1].upper()
        # 识别哪个部分是市场，哪个部分是代码
        if p1 in ["SH", "SZ", "HK", "US"]:
            market, code = p1, parts[1]
        elif p2 in ["SH", "SZ", "HK", "US"]:
            market, code = p2, parts[0]
        else:
            return stock_code.lower()

        if market == "SH":
            return f"sh{code}"
        elif market == "SZ":
            return f"sz{code}"
        elif market == "HK":
            return f"hk{code.zfill(5)}"
        elif market == "US":
            if for_hist:
                suffix = self._us_suffix_map.get(code.upper(), ".OQ")
                return f"us{code}{suffix}"
            return f"us{code}"
        return code.lower()

    def _build_hist_url(self, symbol: str, start_date: str, end_date: str, adj: str, count: int = 1) -> str:
        """构造历史 K 线请求 URL"""
        market = symbol[:2].lower()
        base_url = self._hist_url
        if market == "us":
            base_url = self._us_hist_url
        elif market == "hk":
            base_url = self._hk_hist_url
            
        adj_param = adj if adj in ['qfq', 'hfq'] else ""
        # count 默认为 1，获取指定范围内的记录条数
        param = f"{symbol},day,{start_date},{end_date},{count},{adj_param}"
        return f"{base_url}?param={param}"

    def _fetch_from_snapshot(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        """从快照接口获取数据"""
        symbol = self._transform_symbol(stock_code, for_hist=False)
        url = f"{self._snapshot_url}{symbol}"
        try:
            response = self._session.get(url, timeout=10)
            response.encoding = 'gbk'
            text = response.text
            if not text or "v_pv_none_match" in text or "=" not in text:
                return None
            
            val_part = text.split('=', 1)[1].strip().strip('"').strip(';')
            fields = val_part.split('~')
            
            # 通用索引: 3:Close, 5:Open, 33:High, 34:Low, 6:Volume, 37:Amount
            if len(fields) <= 37:
                return None
                
            open_p, high_p, low_p, close_p = float(fields[5]), float(fields[33]), float(fields[34]), float(fields[3])
            volume = float(fields[6])
            amount = float(fields[37])
            
            market_prefix = symbol[:2].lower()
            if market_prefix in ['sh', 'sz']:
                volume *= 100 # 手 -> 股
                amount *= 10000 # 万元 -> 元
            
            return pd.DataFrame([{
                KlineFields.TRADE_DATE: trade_date.strftime("%Y-%m-%d"),
                KlineFields.STOCK_CODE: stock_code,
                KlineFields.OPEN: open_p, KlineFields.HIGH: high_p, KlineFields.LOW: low_p, KlineFields.CLOSE: close_p,
                KlineFields.VOLUME: int(volume), KlineFields.AMOUNT: amount,
                KlineFields.ADJ_TYPE: AdjType.NONE.value, KlineFields.SOURCE: self.source_name,
                KlineFields.FETCH_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
        except Exception as e:
            logger.debug(f"Snapshot fallback failed for {stock_code}: {e}")
            return None

    def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime, adj: AdjType = AdjType.QFQ) -> Optional[pd.DataFrame]:
        """批量获取历史日K线数据"""
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        symbol = self._transform_symbol(stock_code, for_hist=True)
        adj_val = adj.value if adj else "qfq"
        
        # 腾讯接口 count 为请求的数据量，通常传较大的值以确保覆盖范围
        days_diff = (end_date - start_date).days + 10
        url = self._build_hist_url(symbol, start_str, end_str, adj_val, count=days_diff)
        
        try:
            response = self._session.get(url, timeout=15)
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"Tencent historical error: {data.get('msg', 'Unknown error')}")
                return None
            
            # 提取数据
            market_data = data.get('data', {}).get(symbol, {})
            kline_key = f"{adj_val}day" if adj_val else "day"
            kline_list = market_data.get(kline_key) or market_data.get("day")
            
            if not kline_list:
                return None
            
            # 解析为 DataFrame
            rows = []
            for k in kline_list:
                # 腾讯返回格式通常为 [date, open, close, high, low, volume, ...]
                dt_str = k[0]
                if start_str <= dt_str <= end_str:
                    volume = float(k[5])
                    if symbol.startswith('sh') or symbol.startswith('sz'):
                        volume *= 100
                    
                    rows.append({
                        KlineFields.TRADE_DATE: dt_str,
                        KlineFields.STOCK_CODE: stock_code,
                        KlineFields.OPEN: float(k[1]), 
                        KlineFields.HIGH: float(k[3]), 
                        KlineFields.LOW: float(k[4]),
                        KlineFields.CLOSE: float(k[2]),
                        KlineFields.VOLUME: int(volume),
                        KlineFields.AMOUNT: float(k[2]) * volume, # 估算金额
                        KlineFields.ADJ_TYPE: adj_val,
                        KlineFields.SOURCE: self.source_name,
                        KlineFields.FETCH_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            return pd.DataFrame(rows) if rows else None
            
        except Exception as e:
            logger.error(f"Tencent historical fetch failed for {stock_code}: {e}")
            return None

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime, adj: AdjType = AdjType.NONE) -> Optional[pd.DataFrame]:
        """主入口"""
        date_str = trade_date.strftime("%Y-%m-%d")
        symbol = self._transform_symbol(stock_code, for_hist=True)
        adj_val = adj.value if adj else ""
        
        # 尝试历史接口
        url = self._build_hist_url(symbol, date_str, date_str, adj_val)
        try:
            response = self._session.get(url, timeout=10)
            data = response.json()
            
            # 美股容错：如果失败且带 .OQ，尝试 .N
            if data.get('code') != 0 and "us" in symbol and ".OQ" in symbol:
                symbol_alt = symbol.replace(".OQ", ".N")
                url_alt = self._build_hist_url(symbol_alt, date_str, date_str, adj_val)
                resp_alt = self._session.get(url_alt, timeout=10)
                if resp_alt.status_code == 200:
                    data = resp_alt.json()
                    if data.get('code') == 0:
                        symbol = symbol_alt

            if data.get('code') == 0:
                # 解析 JSON
                market_data = data.get('data', {}).get(symbol, {})
                kline_key = f"{adj_val}day" if adj_val else "day"
                kline_list = market_data.get(kline_key) or market_data.get("day")
                
                if kline_list:
                    # 匹配日期
                    target = next((k for k in kline_list if k[0] == date_str), None)
                    if target:
                        open_p, close_p, high_p, low_p, volume = float(target[1]), float(target[2]), float(target[3]), float(target[4]), float(target[5])
                        if symbol.startswith('sh') or symbol.startswith('sz'):
                            volume *= 100
                        
                        return pd.DataFrame([{
                            KlineFields.TRADE_DATE: date_str,
                            KlineFields.STOCK_CODE: stock_code,
                            KlineFields.OPEN: open_p, KlineFields.HIGH: high_p, KlineFields.LOW: low_p, KlineFields.CLOSE: close_p,
                            KlineFields.VOLUME: int(volume), KlineFields.AMOUNT: close_p * volume,
                            KlineFields.ADJ_TYPE: adj.value if adj else AdjType.NONE.value,
                            KlineFields.SOURCE: self.source_name,
                            KlineFields.FETCH_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }])

            # 若历史接口失败或无数据，降级到快照 (仅支持当日或最后交易日)
            return self._fetch_from_snapshot(stock_code, trade_date)

        except Exception as e:
            logger.error(f"Tencent fetch error ({stock_code}): {e}")
            return self._fetch_from_snapshot(stock_code, trade_date)
