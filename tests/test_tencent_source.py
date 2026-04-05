from src.data_sources.tencent_source import TencentDataSource
from datetime import datetime
import pandas as pd

def test_tencent_source():
    source = TencentDataSource()
    
    # Test health check
    health = source.health_check()
    print(f"Health check: {health}")
    
    today = datetime.now()
    
    # Test A-Share (Kweichow Moutai)
    print("\nTesting A-Share: SH.600519")
    df_a = source.fetch_daily_kline("SH.600519", today)
    if df_a is not None:
        print(df_a)
    else:
        print("Failed to fetch A-Share data")

    # Test HK (Tencent)
    print("\nTesting HK: HK.00700")
    df_hk = source.fetch_daily_kline("HK.00700", today)
    if df_hk is not None:
        print(df_hk)
    else:
        print("Failed to fetch HK data")

    # Test US (Apple)
    print("\nTesting US: US.AAPL")
    df_us = source.fetch_daily_kline("US.AAPL", today)
    if df_us is not None:
        print(df_us)
    else:
        print("Failed to fetch US data")

if __name__ == "__main__":
    test_tencent_source()
