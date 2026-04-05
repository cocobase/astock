import sys
import os
from datetime import datetime

# 将项目根目录添加到 python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_sources.futu_source import FutuDataSource

def test_futu_source():
    # 默认配置
    host = "127.0.0.1"
    port = 11111
    
    source = FutuDataSource(host=host, port=port)
    
    print(f"正在测试富途数据源 ({host}:{port})...")
    
    # 检查连通性
    if not source.health_check():
        print("错误: 无法连接至 FutuOpenD，请确保 FutuOpenD 已启动并已登录。")
        return

    print("连接成功！")

    # 测试获取数据 (以 腾讯 00700.HK 为例，日期设为最近的一个交易日)
    # 注意：历史K线接口可能需要对应的市场权限
    test_code = 'HK.00700'
    test_date = datetime(2026, 3, 30) # 假设 2026-03-30 是交易日
    
    print(f"尝试获取 {test_code} 在 {test_date.strftime('%Y-%m-%d')} 的数据...")
    df = source.fetch_daily_kline(test_code, test_date)
    
    if df is not None and not df.empty:
        print("成功获取数据:")
        print(df)
    else:
        print(f"未获取到数据，可能是非交易日或权限限制。请检查日志。")

    source.close()

if __name__ == "__main__":
    test_futu_source()
