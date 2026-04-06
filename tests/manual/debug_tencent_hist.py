import requests
import json
from datetime import datetime
import pandas as pd
import os

def test_tencent_hist_api(symbol, start_date, end_date, adj_type=""):
    """
    测试腾讯历史K线接口
    adj_type: qfq (前复权), hfq (后复权), "" (不复权)
    """
    # 腾讯内部 symbol 转换 (SH.600519 -> sh600519)
    # 这里为了测试直接传原始格式
    
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"{symbol},day,{start_date},{end_date},10,{adj_type}"
    }
    
    print(f"\n[测试] 请求接口: {symbol} | 日期: {start_date} ~ {end_date} | 复权: {adj_type or 'none'}")
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            print(f"[-] 接口返回错误码: {data.get('code')}")
            return None
        
        # 提取数据路径
        # 结构通常是 data[symbol]['day'] 或 data[symbol]['qfqday']
        stock_data = data.get("data", {}).get(symbol, {})
        
        day_key = "day" if not adj_type else f"{adj_type}day"
        kline_list = stock_data.get(day_key, [])
        
        if not kline_list:
            # 有时候即使传了 qfq，返回的 key 可能还是 day，或者在某些市场下不支持
            kline_list = stock_data.get("day", [])
            
        if not kline_list:
            print(f"[-] 未找到 K 线数据. 完整响应结构预览: {list(stock_data.keys())}")
            return None
            
        print(f"[+] 成功获取 {len(kline_list)} 条记录")
        # 打印第一条数据及其索引
        first_row = kline_list[0]
        print(f"首条数据详情: {first_row}")
        for i, val in enumerate(first_row):
            print(f"  索引 {i}: {val}")
            
        return kline_list
    except Exception as e:
        print(f"[-] 请求异常: {e}")
        return None

def main():
    test_cases = [
        {"symbol": "sh600519", "name": "贵州茅台 (A)", "date": "2026-04-03"},
        {"symbol": "hk00700",  "name": "腾讯控股 (HK)", "date": "2026-04-02"},
        {"symbol": "usAAPL",   "name": "苹果 (US)", "date": "2026-03-31"},
    ]
    
    for case in test_cases:
        # 特别为美股增加一个范围测试
        if "US" in case['name']:
            print(f"\n{'='*20} {case['name']} (范围测试) {'='*20}")
            test_tencent_hist_api(case['symbol'], "2026-03-20", "2026-04-02", "qfq")
            
        print(f"\n{'='*20} {case['name']} {'='*20}")
        res_none = test_tencent_hist_api(case['symbol'], case['date'], case['date'], "")
        res_qfq = test_tencent_hist_api(case['symbol'], case['date'], case['date'], "qfq")
        
        # 3. 验证数据逻辑 (以 A 股为例校准单位)
        if case['symbol'] == "sh600519" and res_none:
            row = res_none[0]
            # 索引通常是: 0:日期, 1:开, 2:收, 3:高, 4:低, 5:成交量
            # 贵州茅台 4-3 收盘价 1460 左右
            print(f"\n[验证] 价格校验: 收盘价={row[2]}, 开盘={row[1]}")
            # 成交量单位校验
            # 快照接口返回的是 手，历史接口可能是 手 也可能是 股
            print(f"[验证] 成交量校验: 原始值={row[5]}")

if __name__ == "__main__":
    main()
