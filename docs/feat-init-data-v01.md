# 方案设计：--init 历史数据初始化功能 (v0.1)

## 1. 目标与定位
为系统提供一键式初始化能力。当执行 `--init` 时，系统将清空本地已存在的市场数据，并根据配置文件中的标的代码列表，批量抓取指定时间范围内的历史日 K 线数据进行重新构建。

## 2. 核心逻辑流程
1.  **参数解析**：识别 `--init` 选项，可选配合 `--days`（默认 365 天）指定历史深度。
2.  **安全确认**：在终端显示警告信息，并要求用户手动输入 `y` 确认后方可继续。
3.  **精准清理**：遍历并删除 `data/` 目录下的所有市场文件夹（如 `A-Share/`, `HK/`, `US/`），但保留 `data/` 根目录本身。
4.  **批量抓取**：
    *   遍历所有市场及标的。
    *   调用数据源的历史数据接口（`fetch_historical_kline`）。
5.  **高效存储**：将获取到的历史数据 DataFrame 按年/月规则直接写入 CSV。

## 3. 详细设计修改点

### 3.1 命令行接口 (`src/main.py`)
新增 `--init` 参数，并与 `--run`、`--status` 互斥。
```python
parser.add_argument("--init", action="store_true", help="初始化历史K线数据（会清空现有数据）")
parser.add_argument("--days", type=int, default=365, help="初始化历史天数，默认365天")
```

**交互确认逻辑示例：**
```python
if args.init:
    confirm = input("[WARNING] 此操作将清空所有已下载的市场数据！是否继续? [y/N]: ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
```

### 3.2 数据源接口扩展 (`src/data_sources/base.py`)
在 `BaseDataSource` 中增加历史数据获取抽象方法。
```python
@abstractmethod
def fetch_historical_kline(self, stock_code: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
    """获取指定时间段的历史日K线数据"""
    pass
```

### 3.3 存储层清理逻辑 (`src/core/storage.py`)
增加精准清理方法。
```python
def clear_market_data(self):
    """
    清理逻辑：仅删除 data/ 下的市场子目录，保留根目录。
    """
    import shutil
    for item in os.listdir(self.root_path):
        item_path = os.path.join(self.root_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
            logger.warning(f"已清理市场目录: {item_path}")
```

## 4. 关键实现考量

### 4.1 数据一致性
*   **清理范围**：通过 `os.listdir` 遍历 `root_path`，仅对目录执行 `rmtree`，确保非数据文件（如 `.gitkeep` 或其他配置文件）不受影响。
*   **历史补齐**：初始化时，数据源应尽可能一次性拉取完整 DataFrame，避免高频单次请求。

### 4.2 交互体验
*   执行 `python main.py --init` 时，控制台应输出：
    ```text
    [WARNING] 检测到 --init 参数，将清空 ./data 下的所有市场数据目录！
    [PROMPT] 是否确认执行? [y/N]: y
    [INFO] 正在清理 ./data/A-Share ... 完成。
    [INFO] 正在清理 ./data/HK ... 完成。
    [INFO] 开始初始化历史数据，深度: 365天 (2025-04-06 至 2026-04-06)
    ...
    ```
