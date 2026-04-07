import os
import shutil
from typing import List, Optional, Union
import pandas as pd
from loguru import logger
from .base import BaseStorage
from src.models import KlineData


class CsvStorage(BaseStorage):
    """基于 CSV 的文件存储实现"""

    def __init__(self, root_path: str = "./data"):
        self.root_path = root_path
        if not os.path.exists(root_path):
            os.makedirs(root_path)
            logger.info(f"创建数据根目录: {root_path}")

    def _get_clean_code(self, stock_code: str) -> str:
        """代码格式转换逻辑（原逻辑迁移）"""
        code = stock_code.strip().upper()
        if code.startswith("HK."):
            # 去除前缀并填充为 5 位
            return code.replace("HK.", "").zfill(5)
        if code.startswith(("SH.", "SZ.", "US.")):
            return code.split(".")[-1]
        return code

    def get_data_path(self, stock_code: str, market: str) -> str:
        """根据市场和代码生成存储路径"""
        market_dir = os.path.join(self.root_path, market)
        if not os.path.exists(market_dir):
            os.makedirs(market_dir)
        
        clean_code = self._get_clean_code(stock_code)
        return os.path.join(market_dir, f"{clean_code}.csv")

    def save_data(self, data: Union[pd.DataFrame, List[KlineData]], market: str) -> bool:
        """保存数据，支持全量保存（原 save_data 逻辑）"""
        if data is None:
            return False

        # 如果是模型列表，先转成 DataFrame
        if isinstance(data, list):
            df = pd.DataFrame([item.to_dict() for item in data])
        else:
            df = data

        if df.empty:
            return False

        stock_code = df.iloc[0]["stock_code"]
        file_path = self.get_data_path(stock_code, market)

        try:
            if os.path.exists(file_path):
                existing_df = pd.read_csv(file_path)
                # 合并并根据 trade_date 去重
                combined_df = pd.concat([existing_df, df]).drop_duplicates(subset=["trade_date"], keep="last")
                combined_df = combined_df.sort_values("trade_date")
                combined_df.to_csv(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            logger.error(f"保存 CSV 失败 ({stock_code}): {e}")
            return False

    def get_last_n_rows(self, stock_code: str, n: int = 1) -> Optional[pd.DataFrame]:
        """获取最近 N 行数据，支持模糊匹配（原逻辑迁移）"""
        clean_code = self._get_clean_code(stock_code)
        
        # 遍历子目录寻找对应文件
        for market in os.listdir(self.root_path):
            market_path = os.path.join(self.root_path, market)
            if not os.path.isdir(market_path):
                continue
            
            file_path = os.path.join(market_path, f"{clean_code}.csv")
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    return df.tail(n)
                except Exception as e:
                    logger.error(f"读取数据失败 ({stock_code}): {e}")
        return None

    def clear_market_data(self, market: Optional[str] = None) -> bool:
        """清理数据目录（原 clear_market_data 逻辑）"""
        try:
            if market:
                target_path = os.path.join(self.root_path, market)
            else:
                target_path = self.root_path
                
            if os.path.exists(target_path):
                for item in os.listdir(target_path):
                    item_path = os.path.join(target_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                logger.info(f"已清理目录: {target_path}")
            return True
        except Exception as e:
            logger.error(f"清理数据失败: {e}")
            return False
