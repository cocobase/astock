import pandas as pd
from datetime import datetime
from loguru import logger
from src.data_sources.yfinance_source import YFinanceDataSource
from src.data_sources.tencent_source import TencentDataSource
import sys

def compare_data(stock_code: str, market_name: str, target_date: datetime):
    print(f"\n{'='*20} 正在对比市场: {market_name} | 标的: {stock_code} {'='*20}")
    
    # 强制不使用代理进行测试，如果环境需要请根据 proxies.txt 手动修改
    yf_source = YFinanceDataSource()
    tn_source = TencentDataSource()
    
    print(f"请求 yfinance 日期: {target_date.strftime('%Y-%m-%d')}")
    print(f"请求 tencent  日期: {datetime.now().strftime('%Y-%m-%d')} (实时快照)")
    
    # yfinance 获取指定日期的数据
    df_yf = yf_source.fetch_daily_kline(stock_code, target_date)
    # tencent 只能获取当前快照（如果是周末或节假日，它返回最后一个交易日数据）
    df_tn = tn_source.fetch_daily_kline(stock_code, datetime.now())
    
    if df_yf is None or df_tn is None:
        if df_yf is None: print(f"[-] yfinance 未能获取到 {target_date.strftime('%Y-%m-%d')} 的数据")
        if df_tn is None: print(f"[-] tencent 未能获取到实时快照")
        return

    yf = df_yf.iloc[0]
    tn = df_tn.iloc[0]
    
    print(f"yfinance 实际日期: {yf['trade_date']}")
    print(f"tencent  实际日期: {tn['trade_date']}")
    
    # 打印对比表格
    print(f"{'字段':<15} | {'yfinance':<20} | {'tencent':<20} | {'差异 (abs/%)':<15}")
    print("-" * 85)
    
    fields_to_compare = [
        ("open", "开盘价"),
        ("high", "最高价"),
        ("low", "最低价"),
        ("close", "收盘价"),
        ("volume", "成交量"),
        ("amount", "成交额"),
    ]
    
    for field, label in fields_to_compare:
        val_yf = yf[field]
        val_tn = tn[field]
        
        diff_str = ""
        if isinstance(val_yf, (int, float, complex)) and isinstance(val_tn, (int, float, complex)):
            if val_yf != 0:
                diff_val = abs(val_yf - val_tn)
                diff_pct = (diff_val / val_yf) * 100
                diff_str = f"{diff_val:.2f} ({diff_pct:.2f}%)"
            else:
                diff_str = "N/A"
        else:
            diff_str = "一致" if val_yf == val_tn else "不一致"
            
        print(f"{label:<15} | {str(val_yf):<20} | {str(val_tn):<20} | {diff_str:<15}")

    print(f"\n[!] 数据源备注:")
    print(f"    - yfinance 复权类型: {yf['adj_type']}")
    print(f"    - tencent  复权类型: {tn['adj_type']}")
    print(f"    - 注意: yfinance 通常提供前复权数据(qfq)，而 tencent 实时接口提供不复权数据(none)，")
    print(f"      这在除权除息后的股票上会导致价格有显著差异。")

def main():
    # 2026-04-06 是周一。
    # 我们尝试对比最新的历史交易日数据
    test_cases = [
        ("SH.600519", "A-Share (贵州茅台)", datetime(2026, 4, 3)),
        ("HK.00700", "HK (腾讯控股)", datetime(2026, 4, 2)),
        ("US.AAPL", "US (苹果)", datetime(2026, 4, 2)),
    ]
    
    for code, market, target_date in test_cases:
        try:
            compare_data(code, market, target_date)
        except Exception as e:
            print(f"对比 {code} 时发生异常: {e}")

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    main()
