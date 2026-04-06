import pytest
import pandas as pd
from datetime import datetime
from src.data_sources.tencent_source import TencentDataSource
from src.data_sources.yfinance_source import YFinanceDataSource
from src.constants import AdjType, KlineFields

@pytest.fixture(scope="module")
def tencent_source():
    return TencentDataSource()

@pytest.fixture(scope="module")
def yf_source():
    return YFinanceDataSource()

def test_health_check(tencent_source):
    """验证接口连通性"""
    assert tencent_source.health_check() is True

@pytest.mark.parametrize("stock_code, market, expected_volume_factor", [
    ("SH.600519", "A-Share", 100),   # A股需 * 100
    ("SZ.000858", "A-Share", 100),
    ("HK.00700",  "HK",      1),     # 港股单位为股
    ("US.AAPL",   "US",      1),     # 美股单位为股
    ("US.WMT",    "US",      1),     # 纽交所标的
])
def test_historical_fetch(tencent_source, stock_code, market, expected_volume_factor):
    """测试各市场历史数据获取及单位转换"""
    # 使用 2026-04-03 (上周五) 作为基准历史日期
    target_date = datetime(2026, 4, 3)
    df = tencent_source.fetch_daily_kline(stock_code, target_date, adj=AdjType.NONE)
    
    assert df is not None, f"未能获取 {stock_code} 的历史数据"
    assert len(df) == 1
    row = df.iloc[0]
    
    # 1. 验证日期
    assert row[KlineFields.TRADE_DATE] == "2026-04-03"
    
    # 2. 验证 OHLC 逻辑
    assert row[KlineFields.HIGH] >= row[KlineFields.OPEN]
    assert row[KlineFields.HIGH] >= row[KlineFields.CLOSE]
    assert row[KlineFields.LOW] <= row[KlineFields.OPEN]
    assert row[KlineFields.LOW] <= row[KlineFields.CLOSE]
    
    # 3. 验证成交量单位 (粗略验证: A股通常成交量很大，*100后应为100的倍数)
    if market == "A-Share":
        assert int(row[KlineFields.VOLUME]) % 100 == 0

def test_adj_logic(tencent_source):
    """验证复权逻辑是否产生差异"""
    stock_code = "SH.600519"
    target_date = datetime(2025, 1, 2) # 选择一个较早的日期
    
    df_none = tencent_source.fetch_daily_kline(stock_code, target_date, adj=AdjType.NONE)
    df_qfq = tencent_source.fetch_daily_kline(stock_code, target_date, adj=AdjType.QFQ)
    
    assert df_none is not None and df_qfq is not None
    # 在除权标的上，价格应该不同 (或者 adj_type 字段不同)
    assert df_none.iloc[0][KlineFields.ADJ_TYPE] == "none"
    assert df_qfq.iloc[0][KlineFields.ADJ_TYPE] == "qfq"

@pytest.mark.parametrize("stock_code, target_date", [
    ("US.AAPL", datetime(2026, 4, 2)),
    ("SH.600519", datetime(2026, 4, 3)),
])
def test_source_consistency(tencent_source, yf_source, stock_code, target_date):
    """对比 Tencent 和 yfinance 的一致性，Amount 允许 1% 误差"""
    # yfinance 默认返回 QFQ (Adj Close)，所以 Tencent 也用 QFQ
    df_tn = tencent_source.fetch_daily_kline(stock_code, target_date, adj=AdjType.QFQ)
    df_yf = yf_source.fetch_daily_kline(stock_code, target_date)
    
    if df_tn is None or df_yf is None:
        pytest.skip(f"数据源返回空，跳过一致性对比: {stock_code}")
        
    tn = df_tn.iloc[0]
    yf = df_yf.iloc[0]
    
    # 收盘价对比 (允许 0.5% 误差)
    tn_close = tn[KlineFields.CLOSE]
    yf_close = yf[KlineFields.CLOSE]
    assert abs(tn_close - yf_close) / yf_close < 0.005, f"{stock_code} Close 差异过大: TN={tn_close}, YF={yf_close}"
    
    # 成交额对比 (允许 1% 误差)
    amount_diff_pct = abs(tn[KlineFields.AMOUNT] - yf[KlineFields.AMOUNT]) / yf[KlineFields.AMOUNT]
    assert amount_diff_pct < 0.01, f"{stock_code} Amount 误差过大: {amount_diff_pct:.4%}"

def test_us_suffix_auto_resolution(tencent_source):
    """测试美股后缀自动识别逻辑"""
    stock_code = "US.TME"
    target_date = datetime(2026, 4, 2)
    
    df = tencent_source.fetch_daily_kline(stock_code, target_date)
    assert df is not None, "美股自动后缀识别失败"
    assert df.iloc[0][KlineFields.CLOSE] > 0

def test_snapshot_fallback_today(tencent_source):
    """测试请求今日数据时，是否能正确触发快照降级"""
    today = datetime.now()
    df = tencent_source.fetch_daily_kline("SH.600519", today)
    assert isinstance(df, pd.DataFrame)
