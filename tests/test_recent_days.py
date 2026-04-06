import sys
import os
from datetime import datetime
from typing import List

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trading_calendar.checker import CalendarChecker

def test_recent_days():
    checker = CalendarChecker()
    exchanges = ["XSHG", "XNYS", "XHKG"]
    days_to_fetch = 5
    
    print(f"--- 测试获取最近 {days_to_fetch} 个交易日 ---")
    
    for ex in exchanges:
        print(f"\n[交易所: {ex}]")
        try:
            days = checker.get_recent_trading_days(ex, days_to_fetch)
            for i, d in enumerate(days):
                print(f"  {i+1}. {d.strftime('%Y-%m-%d')}")
            
            assert len(days) == days_to_fetch
            assert all(isinstance(d, datetime) for d in days)
            # 验证是升序
            assert all(days[i] < days[i+1] for i in range(len(days)-1))
            
        except Exception as e:
            import traceback
            print(f"  获取失败: {e}")
            traceback.print_exc()

    # 测试指定结束日期 (例如测试 2026-02-15，这是一个周日)
    print("\n[测试指定结束日期: 2026-02-15 (周日), 交易所: XSHG]")
    end_dt = datetime(2026, 2, 15)
    days = checker.get_recent_trading_days("XSHG", 3, end_date=end_dt)
    for i, d in enumerate(days):
        print(f"  {i+1}. {d.strftime('%Y-%m-%d')}")
    
    # 2026-02-15 之前应该是 2-13(五), 2-12(四), 2-11(三)
    expected = ["2026-02-11", "2026-02-12", "2026-02-13"]
    actual = [d.strftime('%Y-%m-%d') for d in days]
    assert actual == expected
    print("  验证通过!")

if __name__ == "__main__":
    test_recent_days()
