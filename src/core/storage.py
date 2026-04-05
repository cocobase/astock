import os
import pandas as pd
from loguru import logger
from src.constants import STANDARD_FIELDS

class CsvStorage:
    def __init__(self, root_path="./data"):
        self.root_path = root_path

    def _get_file_path(self, market_name: str, stock_code: str, trade_date: str) -> str:
        """
        根据规则生成文件路径: data/{market}/{year}/{market}_{code}_daily_kline.csv
        """
        year = trade_date[:4]
        market_dir = os.path.join(self.root_path, market_name, year)
        if not os.path.exists(market_dir):
            os.makedirs(market_dir)
        
        # 将代码中的特殊字符（如点）进行替换或清理，防止文件名问题
        clean_code = stock_code.replace('.', '_')
        file_name = f"{market_name}_{clean_code}_daily_kline.csv"
        return os.path.join(market_dir, file_name)

    def save_data(self, df: pd.DataFrame, market_name: str):
        """
        保存 DataFrame 到 CSV，支持增量写入和去重。
        """
        if df is None or df.empty:
            return

        for _, row in df.iterrows():
            stock_code = row["stock_code"]
            trade_date = row["trade_date"]
            file_path = self._get_file_path(market_name, stock_code, trade_date)
            
            # 增量写入逻辑
            if os.path.exists(file_path):
                # 检查是否已存在该日期的数据
                existing_df = pd.read_csv(file_path)
                if trade_date in existing_df["trade_date"].values.tolist():
                    logger.debug(f"跳过重复数据: {stock_code} @ {trade_date}")
                    continue
                
                # 追加模式
                row.to_frame().T.to_csv(file_path, mode='a', header=False, index=False)
                logger.info(f"追加数据成功: {stock_code} @ {trade_date} -> {file_path}")
            else:
                # 首次创建
                row.to_frame().T.to_csv(file_path, mode='w', header=True, index=False)
                logger.info(f"首次创建并保存数据: {stock_code} @ {trade_date} -> {file_path}")
