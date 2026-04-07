import pytest
import os
import shutil
import asyncio
import pandas as pd
from datetime import datetime
from src.models import KlineData, MarketStatus
from src.core.storage.csv_impl import CsvStorage
from src.data_sources.manager import DataSourceManager
from src.data_sources.base import BaseDataSource
from typing import Optional


# --- 1. Models Tests ---

def test_kline_data_model():
    """测试 KlineData 模型"""
    kline = KlineData(
        trade_date="2026-04-07",
        stock_code="600519.SH",
        open=1800.0,
        high=1850.0,
        low=1780.0,
        close=1820.0,
        volume=50000,
        source="test_source"
    )
    assert kline.trade_date == "2026-04-07"
    assert kline.close == 1820.0
    d = kline.to_dict()
    assert d["stock_code"] == "600519.SH"
    assert d["source"] == "test_source"


def test_market_status_model():
    """测试 MarketStatus 模型"""
    status = MarketStatus(
        market_name="A-Share",
        exchange_code="XSHG",
        timezone="Asia/Shanghai",
        market_now="2026-04-07 15:00:00",
        market_date="2026-04-07",
        is_trading_day_today=True,
        is_current_session_closed=True,
        last_trading_day="2026-04-07"
    )
    assert status.market_name == "A-Share"
    assert status.is_trading_day_today is True


# --- 2. Storage Tests ---

def test_csv_storage_implementation():
    """测试 CsvStorage 接口实现"""
    test_root = "./test_data_refactor"
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    
    storage = CsvStorage(root_path=test_root)
    
    # 测试数据路径生成
    path = storage.get_data_path("HK.00700", "HK")
    assert "HK" in path
    assert "00700.csv" in path
    
    # 测试保存模型数据
    kline = KlineData("2026-01-01", "HK.00700", 300.0, 310.0, 290.0, 305.0, 1000000, source="test")
    success = storage.save_data([kline], "HK")
    assert success is True
    assert os.path.exists(path)
    
    # 测试读取最近数据
    last_n = storage.get_last_n_rows("HK.00700", 1)
    assert last_n is not None
    assert len(last_n) == 1
    assert last_n.iloc[0]["close"] == 305.0
    
    shutil.rmtree(test_root)


# --- 3. Async Manager Tests ---

class MockDataSource(BaseDataSource):
    """用于测试的模拟数据源"""
    def fetch_daily_kline(self, stock_code: str, trade_date: datetime) -> Optional[pd.DataFrame]:
        # 模拟同步阻塞调用
        return pd.DataFrame([{
            "trade_date": trade_date.strftime("%Y-%m-%d"),
            "stock_code": stock_code,
            "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0,
            "volume": 1000, "source": self.source_name
        }])

    def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        return pd.DataFrame([{
            "trade_date": start_date.strftime("%Y-%m-%d"),
            "stock_code": stock_code,
            "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0,
            "volume": 1000, "source": self.source_name
        }])


@pytest.mark.asyncio
async def test_manager_async_fetch():
    """测试 DataSourceManager 的异步抓取和频率控制"""
    manager = DataSourceManager(request_interval=0.1)
    mock_source = MockDataSource("mock")
    manager.register_source(mock_source)
    
    start_time = asyncio.get_event_loop().time()
    
    # 并发执行两次请求，验证频率控制（request_interval=0.1）
    t1 = manager.fetch_async_with_failover(["mock"], "TEST.CODE", datetime(2026, 4, 7))
    t2 = manager.fetch_async_with_failover(["mock"], "TEST.CODE", datetime(2026, 4, 7))
    
    results = await asyncio.gather(t1, t2)
    end_time = asyncio.get_event_loop().time()
    
    assert len(results) == 2
    assert results[0] is not None
    # 两次请求至少应该耗时 0.2s (2 * 0.1s 间隔)
    assert end_time - start_time >= 0.2
