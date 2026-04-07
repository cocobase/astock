import pandas as pd
import os
from loguru import logger
from src.core.storage import CsvStorage
from src.core.config_loader import ConfigLoader

class DataAnalyzer:
    def __init__(self, storage: CsvStorage, config_loader: ConfigLoader):
        self.storage = storage
        self.config_loader = config_loader

    def calculate_pct_change(self):
        """
        计算配置文件中所有股票的最新收盘涨幅，并导出 CSV。
        """
        market_configs = self.config_loader.config.get("market_configs", {})
        results = []

        for market_name, m_config in market_configs.items():
            codes = m_config.get("codes", [])
            logger.info(f"开始计算市场 {market_name} 的涨幅 (共 {len(codes)} 个标的)")

            for code in codes:
                # CsvStorage.get_last_n_rows 接口现在是 (stock_code, n)
                df = self.storage.get_last_n_rows(code, n=2)
                
                if df is None or df.empty:
                    logger.warning(f"标的 {code} ({market_name}) 无本地数据，跳过")
                    continue

                # 提取最后一行数据
                last_row = df.iloc[-1]
                
                # 计算涨幅
                pct_change = 0.0
                if len(df) >= 2:
                    second_last_close = df.iloc[-2]["close"]
                    last_close = last_row["close"]
                    if second_last_close != 0:
                        pct_change = (last_close - second_last_close) / second_last_close * 100
                else:
                    logger.warning(f"标的 {code} ({market_name}) 仅有 1 天数据，涨幅设为 0.00")

                results.append({
                    "symbol": code,
                    "open": round(last_row["open"], 2),
                    "high": round(last_row["high"], 2),
                    "low": round(last_row["low"], 2),
                    "close": round(last_row["close"], 2),
                    "pct-change": round(pct_change, 2)
                })

        if not results:
            logger.error("没有任何有效数据用于计算涨幅")
            return

        # 构造结果 DataFrame
        output_df = pd.DataFrame(results)
        
        # 确保输出目录存在
        output_path = os.path.join(self.storage.root_path, "pct-change.csv")
        output_df.to_csv(output_path, index=False)
        
        logger.info(f"涨幅计算完成，结果保存至: {output_path}")
        return output_path
