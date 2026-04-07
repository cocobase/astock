import os
import pandas as pd
from loguru import logger
from src.constants import STANDARD_FIELDS

class CsvStorage:
    def __init__(self, root_path="./data"):
        self.root_path = root_path

    def _get_clean_code(self, market_name: str, stock_code: str) -> str:
        """
        统一清理代码：去掉市场前缀/后缀，并对港股补零。
        """
        clean_code = stock_code
        # 去掉前缀
        for prefix in ["HK.", "SH.", "SZ.", "US.", "HK_", "SH_", "SZ_", "US_"]:
            if clean_code.startswith(prefix):
                clean_code = clean_code[len(prefix):]
        # 去掉后缀
        if "." in clean_code:
            parts = clean_code.split(".")
            if parts[-1].upper() in ["HK", "SH", "SZ", "US"]:
                clean_code = parts[0]
        
        # 替换剩余的点
        clean_code = clean_code.replace('.', '_')

        # 港股补零
        if market_name == "HK" and clean_code.isdigit():
            clean_code = clean_code.zfill(5)
            
        return clean_code

    def _get_file_path(self, market_name: str, stock_code: str, trade_date: str) -> str:
        """
        根据规则生成文件路径: data/{market}/{year}/{market}_{code}_daily_kline.csv
        """
        year = trade_date[:4]
        market_dir = os.path.join(self.root_path, market_name, year)
        if not os.path.exists(market_dir):
            os.makedirs(market_dir)
        
        clean_code = self._get_clean_code(market_name, stock_code)
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

    def _find_available_years(self, market_name: str) -> list:
        """
        获取指定市场下所有可用的年份目录，并按从新到旧排序。
        """
        market_path = os.path.join(self.root_path, market_name)
        if not os.path.exists(market_path):
            return []
        
        years = [d for d in os.listdir(market_path) if os.path.isdir(os.path.join(market_path, d)) and d.isdigit()]
        return sorted(years, reverse=True)

    def get_last_n_rows(self, market_name: str, stock_code: str, n: int = 2) -> pd.DataFrame:
        """
        根据规则跨年份获取指定标的的最后 n 行数据。
        """
        years = self._find_available_years(market_name)
        combined_df = pd.DataFrame()
        
        clean_code = self._get_clean_code(market_name, stock_code)
        target_file_name = f"{market_name}_{clean_code}_daily_kline.csv"

        for year in years:
            year_dir = os.path.join(self.root_path, market_name, year)
            file_path = os.path.join(year_dir, target_file_name)
            
            # 如果标准路径不存在，尝试模糊搜索包含 clean_code 的文件（兼容旧格式）
            if not os.path.exists(file_path):
                if os.path.exists(year_dir):
                    potential_files = [f for f in os.listdir(year_dir) if clean_code in f and f.endswith(".csv")]
                    if potential_files:
                        # 找到多个时取第一个（通常只有一个）
                        file_path = os.path.join(year_dir, potential_files[0])
                        logger.debug(f"通过模糊匹配找到数据文件: {file_path}")

            if os.path.exists(file_path):
                # 考虑到文件可能较小（一年约250行），直接读取。如果后续文件巨大，可优化为从末尾 seek。
                try:
                    df = pd.read_csv(file_path)
                    if not df.empty:
                        # 取当前文件的最后几行
                        current_rows = df.tail(n - len(combined_df))
                        combined_df = pd.concat([current_rows, combined_df], ignore_index=True)
                except Exception as e:
                    logger.error(f"读取文件 {file_path} 失败: {e}")
                
                if len(combined_df) >= n:
                    break
        
        return combined_df.tail(n)

    def save_data(self, df: pd.DataFrame, market_name: str):
        """
        保存 DataFrame 到 CSV，支持增量写入和去重。
        优化：针对多行数据进行批量处理，减少 IO 次数。
        增强：强制按照 STANDARD_FIELDS 排序，确保列顺序始终一致。
        """
        if df is None or df.empty:
            return

        # 强制列重排，确保不一致的数据源也能按标准落盘
        try:
            df = df[STANDARD_FIELDS]
        except KeyError as e:
            logger.error(f"保存数据失败，缺失必要字段: {e}")
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
