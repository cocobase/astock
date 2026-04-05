import requests
import pandas as pd
from datetime import datetime
from typing import Optional
from loguru import logger
from src.data_sources.base import BaseDataSource
from src.constants import KlineFields, AdjType

class TencentDataSource(BaseDataSource):
    """
    腾讯财经数据源，提供 A 股、港股、美股的实时行情快照。
    由于该接口仅提供当前快照，fetch_daily_kline 仅在 trade_date 为当前交易日时有效。
    """
    def __init__(self, proxy: Optional[str] = None):
        self._source_name = "tencent"
        self._base_url = "https://qt.gtimg.cn/q="
        self._proxy = proxy
        self._session = requests.Session()
        if self._proxy:
            self._session.proxies = {
                'http': self._proxy,
                'https': self._proxy,
            }

    @property
    def source_name(self) -> str:
        return self._source_name

    def health_check(self) -> bool:
        """检查腾讯接口连通性"""
        try:
            # 使用上证指数代码进行健康检查
            response = self._session.get(f"{self._base_url}sh000001", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Tencent DataSource health check failed: {e}")
            return False

    def _convert_code(self, stock_code: str) -> str:
        """
        将代码转换为腾讯识别的格式
        SH.600519 -> sh600519
        SZ.000001 -> sz000001
        HK.00700  -> hk00700
        US.AAPL   -> usAAPL
        """
        parts = stock_code.split('.')
        if len(parts) != 2:
            return stock_code
        
        market, code = parts
        if market == "SH":
            return f"sh{code}"
        elif market == "SZ":
            return f"sz{code}"
        elif market == "HK":
            # 补齐 5 位
            return f"hk{code.zfill(5)}"
        elif market == "US":
            return f"us{code}"
        return code

    def _parse_trade_date(self, fields: list) -> Optional[str]:
        """
        根据不同市场定义的索引解析交易日期：
        A股: 索引 30 (YYYYMMDDHHMMSS)
        港股: 索引 30 (YYYY/MM/DD HH:MM:SS) - 文档说是 28，实测 30
        美股: 索引 30 (YYYY-MM-DD HH:MM:SS) - 文档说是 28，实测 30
        """
        try:
            # 统一尝试从索引 30 获取
            if len(fields) <= 30:
                return None
            
            ts_str = fields[30]
            if not ts_str:
                return None
            
            # A股格式: 20260403161427
            if len(ts_str) >= 8 and ts_str[:8].isdigit() and '/' not in ts_str and '-' not in ts_str:
                return f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]}"
            
            # 港股格式: 2026/04/02 16:08:34
            if '/' in ts_str:
                return ts_str.split(' ')[0].replace('/', '-')
            
            # 美股格式: 2026-04-02 16:00:02
            if '-' in ts_str and ' ' in ts_str:
                return ts_str.split(' ')[0]
            
            return None
        except Exception as e:
            logger.debug(f"解析时间戳失败: {e}")
            return None

    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        # 由于腾讯接口仅提供实时快照，如果 trade_date 不是今天，我们无法获取历史 K 线
        # 注意：在实际自动化运行中，收盘后运行此程序，trade_date 应为当日
        now = datetime.now()
        if trade_date.date() != now.date():
            logger.warning(f"Tencent DataSource 仅支持获取当日快照，无法获取历史日期 {trade_date.strftime('%Y-%m-%d')} 的数据")
            return None

        symbol = self._convert_code(stock_code)
        url = f"{self._base_url}{symbol}"
        
        try:
            response = self._session.get(url, timeout=10)
            # 腾讯接口通常返回 GBK
            response.encoding = 'gbk'
            text = response.text
            if not text or "v_pv_none_match" in text:
                logger.warning(f"Tencent 未能获取到数据: {stock_code} ({symbol})")
                return None

            # 解析数据: v_sh600519="1~贵州茅台~600519~1460.00~1459.88~1459.54~...";
            if '=' not in text:
                return None
            
            val_part = text.split('=', 1)[1].strip().strip('"').strip(';')
            fields = val_part.split('~')
            
            # 获取市场前缀
            market_prefix = symbol[:2].lower()
            
            try:
                # 统一字段 (基于观察到的索引)
                # 3: Close, 5: Open, 33: High, 34: Low, 6: Volume, 37: Amount
                open_price = float(fields[5])
                high_price = float(fields[33])
                low_price = float(fields[34])
                close_price = float(fields[3])
                
                if market_prefix in ['sh', 'sz']:
                    # A 股字段
                    volume = float(fields[6]) * 100 # 手 -> 股
                    amount = float(fields[37]) * 10000 # 万元 -> 元
                else:
                    # 港美股字段
                    volume = float(fields[6]) # 股
                    amount = float(fields[37]) # 对应货币单位 (HKD/USD)
            except (IndexError, ValueError) as e:
                logger.error(f"解析数据字段失败 ({stock_code}): {e}")
                return None

            # 获取数据中的实际日期
            real_date = self._parse_trade_date(fields)
            if real_date and real_date != trade_date.strftime("%Y-%m-%d"):
                logger.warning(f"Tencent 接口数据日期 {real_date} 与请求日期 {trade_date.strftime('%Y-%m-%d')} 不一致")
                final_date = real_date
            else:
                final_date = trade_date.strftime("%Y-%m-%d")

            # 统一字段映射
            result_df = pd.DataFrame([{
                KlineFields.TRADE_DATE: final_date,
                KlineFields.STOCK_CODE: stock_code,
                KlineFields.OPEN: open_price,
                KlineFields.HIGH: high_price,
                KlineFields.LOW: low_price,
                KlineFields.CLOSE: close_price,
                KlineFields.VOLUME: volume,
                KlineFields.AMOUNT: amount,
                KlineFields.ADJ_TYPE: AdjType.NONE.value,
                KlineFields.SOURCE: self.source_name,
                KlineFields.FETCH_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])

            return result_df

        except Exception as e:
            logger.error(f"Tencent 获取数据异常 ({stock_code}): {e}")
            return None
