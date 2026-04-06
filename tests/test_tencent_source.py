from src.data_sources.tencent_source import TencentDataSource
from src.constants import AdjType
from datetime import datetime
import pandas as pd

def test_tencent_source():
    source = TencentDataSource()
    
    # 1. 健康检查
    health = source.health_check()
    print(f"Health check: {health}")
    
    # 2. 测试历史日期 (2026-04-03)
    hist_date = datetime(2026, 4, 3)
    
    # 测试 A 股 (贵州茅台) - 不复权
    print("\nTesting A-Share (2026-04-03): SH.600519")
    df_a = source.fetch_daily_kline("SH.600519", hist_date, adj=AdjType.NONE)
    if df_a is not None:
        print(df_a)
        assert df_a.iloc[0]['volume'] > 1000 # 确保单位已转换
    else:
        print("Failed to fetch A-Share data")

    # 测试 A 股 (贵州茅台) - 前复权
    print("\nTesting A-Share QFQ (2026-04-03): SH.600519")
    df_a_qfq = source.fetch_daily_kline("SH.600519", hist_date, adj=AdjType.QFQ)
    if df_a_qfq is not None:
        print(df_a_qfq)
    else:
        print("Failed to fetch A-Share QFQ data")

    # 测试 港股 (腾讯控股)
    print("\nTesting HK (2026-04-03): HK.00700")
    df_hk = source.fetch_daily_kline("HK.00700", hist_date)
    if df_hk is not None:
        print(df_hk)
    else:
        print("Failed to fetch HK data")

    # 测试 美股 (苹果) - 默认尝试 .OQ
    print("\nTesting US (2026-04-03): US.AAPL")
    df_us = source.fetch_daily_kline("US.AAPL", hist_date)
    if df_us is not None:
        print(df_us)
    else:
        print("Failed to fetch US data")

    # 测试 美股 (沃尔玛) - 映射表中的 .N
    print("\nTesting US (2026-04-03): US.WMT (NYSE)")
    df_us_wmt = source.fetch_daily_kline("US.WMT", hist_date)
    if df_us_wmt is not None:
        print(df_us_wmt)
    else:
        print("Failed to fetch US.WMT data")

if __name__ == "__main__":
    test_tencent_source()
