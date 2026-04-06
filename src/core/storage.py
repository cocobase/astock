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

    def clear_market_data(self):
        """
        清理逻辑：仅删除 data/ 下的市场子目录，保留根目录及其中的文件。
        """
        import shutil
        if not os.path.exists(self.root_path):
            return
            
        for item in os.listdir(self.root_path):
            item_path = os.path.join(self.root_path, item)
            if os.path.isdir(item_path):
                try:
                    shutil.rmtree(item_path)
                    logger.warning(f"已清理市场目录: {item_path}")
                except Exception as e:
                    logger.error(f"清理目录 {item_path} 失败: {e}")

    def save_data(self, df: pd.DataFrame, market_name: str):
        """
        保存 DataFrame 到 CSV，支持增量写入和去重。
        优化：针对多行数据进行批量处理，减少 IO 次数。
        """
        if df is None or df.empty:
            return

        # 将 trade_date 转为字符串以方便处理
        if not pd.api.types.is_string_dtype(df["trade_date"]):
            df["trade_date"] = df["trade_date"].dt.strftime("%Y-%m-%d")

        # 按标的和年份分组处理
        for (stock_code, year), group in df.groupby(["stock_code", df["trade_date"].str[:4]]):
            trade_date_sample = group.iloc[0]["trade_date"]
            file_path = self._get_file_path(market_name, stock_code, trade_date_sample)
            
            if os.path.exists(file_path):
                existing_df = pd.read_csv(file_path)
                # 过滤掉已存在的日期
                new_data = group[~group["trade_date"].isin(existing_df["trade_date"].values.tolist())]
                if not new_data.empty:
                    new_data.to_csv(file_path, mode='a', header=False, index=False)
                    logger.info(f"追加 {len(new_data)} 条数据: {stock_code} -> {file_path}")
            else:
                # 首次创建
                group.to_csv(file_path, mode='w', header=True, index=False)
                logger.info(f"首次创建并保存 {len(group)} 条数据: {stock_code} -> {file_path}")
