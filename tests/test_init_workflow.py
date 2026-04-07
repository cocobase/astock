import sys
import os
import shutil
import pandas as pd
from datetime import datetime
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.storage.csv_impl import CsvStorage
from src.data_sources.base import StubDataSource
from src.data_sources.manager import DataSourceManager

def test_storage_clear():
    print("\n--- 测试存储清理逻辑 ---")
    test_root = "./test_data_init"
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    os.makedirs(test_root)
    
    # 创建模拟目录和文件
    os.makedirs(os.path.join(test_root, "A-Share"))
    os.makedirs(os.path.join(test_root, "HK"))
    
    storage = CsvStorage(root_path=test_root)
    storage.clear_market_data()
    
    items = os.listdir(test_root)
    print(f"清理后目录内容: {items}")
    # 新实现会清理整个目录，不再保留 root 下的非目录文件（如果 clear_market_data() 不带参数）
    assert len(items) == 0
    print("✓ 存储清理逻辑验证通过")

def test_init_fetching():
    print("\n--- 测试初始化抓取与批量存储 ---")
    test_root = "./test_data_init"
    storage = CsvStorage(root_path=test_root)
    
    manager = DataSourceManager()
    stub = StubDataSource("stub_init", behavior="success")
    manager.register_source(stub)
    
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 1, 10)
    
    # 模拟抓取
    data = manager.fetch_historical_with_failover(["stub_init"], "000001.SZ", start_date, end_date)
    assert data is not None
    assert len(data) == 3
    
    # 保存
    storage.save_data(data, "A-Share")
    
    # 验证文件 (Phase 3 新结构: root/A-Share/000001.csv)
    file_path = os.path.join(test_root, "A-Share", "000001.csv")
    assert os.path.exists(file_path)
    saved_df = pd.read_csv(file_path)
    assert len(saved_df) == 3
    print("✓ 初始化抓取与批量存储验证通过")

if __name__ == "__main__":
    try:
        test_storage_clear()
        test_init_fetching()
        print("\n所有测试通过！")
    finally:
        if os.path.exists("./test_data_init"):
            shutil.rmtree("./test_data_init")
