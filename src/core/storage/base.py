from abc import ABC, abstractmethod
from typing import List, Optional, Union
import pandas as pd
from src.models import KlineData


class BaseStorage(ABC):
    """存储抽象接口"""

    @abstractmethod
    def save_data(self, data: Union[pd.DataFrame, List[KlineData]], market: str) -> bool:
        """保存单次获取的数据"""
        pass

    @abstractmethod
    def get_last_n_rows(self, stock_code: str, n: int = 1) -> Optional[pd.DataFrame]:
        """获取最近 N 行数据"""
        pass

    @abstractmethod
    def clear_market_data(self, market: Optional[str] = None) -> bool:
        """清理数据"""
        pass

    @abstractmethod
    def get_data_path(self, stock_code: str, market: str) -> str:
        """获取存储路径"""
        pass
