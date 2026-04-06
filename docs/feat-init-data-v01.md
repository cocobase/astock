# 方案设计：--init 历史数据初始化功能 (v0.2)

## 1. 目标与定位
为系统提供一键式初始化能力。当执行 `--init` 时，系统将清空本地已存在的市场数据，并根据配置文件中的标的代码列表，批量抓取指定时间范围内的历史日 K 线数据进行重新构建。

## 2. 核心逻辑流程
1.  **参数解析**：识别 `--init` 选项，可选配合 `--days`（默认 365 天）指定历史深度。
2.  **安全确认**：在终端显示警告信息，并要求用户手动输入 `y` 确认后方可继续。
3.  **精准清理**：遍历并删除 `data/` 目录下的所有市场子文件夹，保留根目录及非目录文件。
4.  **初始化配置**：根据各市场时区（Timezone）计算统一的历史起止日期。
5.  **批量抓取与故障转移**：
    *   调用 `DataSourceManager.fetch_historical_with_failover`。
    *   针对单只标的抓取失败时，记录 Error 日志并跳过，确保整体任务不中断。
6.  **高效存储**：将获取到的历史数据 DataFrame 直接按年/月规则写入 CSV。

## 3. 详细设计修改点

### 3.1 命令行接口 (`src/main.py`)
新增 `--init` 参数，并与 `--run`、`--status` 互斥。
```python
parser.add_argument("--init", action="store_true", help="初始化历史K线数据（会清空现有数据）")
parser.add_argument("--days", type=int, default=365, help="初始化历史天数")
```

### 3.2 数据源层增强
*   **BaseDataSource**: 增加 `fetch_historical_kline(code, start, end)` 抽象方法。
*   **DataSourceManager**: 实现 `fetch_historical_with_failover`，逻辑同单日获取，但调用底层批量接口。

### 3.3 存储层清理逻辑 (`src/core/storage.py`)
增强目录检测，防止路径不存在时报错。
```python
def clear_market_data(self):
    import shutil
    if not os.path.exists(self.root_path):
        return
    for item in os.listdir(self.root_path):
        item_path = os.path.join(self.root_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
            logger.warning(f"已清理市场目录: {item_path}")
```

## 4. 关键实现考量

### 4.1 异常容错 (Robustness)
*   **Symbol-level Isolation**: 初始化过程中，若某一标的由于 API 配额或网络问题失败，系统必须 `catch` 异常，记录 `log_detail` 后继续处理下一只标的。
*   **Rate Limiting**: 在处理不同市场或大批量标的时，在循环中加入 `time.sleep(1)`，降低被封 IP 风险。

### 4.2 时区对齐 (Timezone Alignment)
*   使用 `CalendarChecker` 获取各市场当前时间，回溯 `N` 天计算 `start_date`。
*   确保 `end_date` 为该市场最后一个完整的交易日。

## 5. 测试方案 (Testing Strategy)

### 5.1 单元测试
*   **CLI 互斥性**: 验证 `python main.py --init --run` 抛出 ArgumentError。
*   **清理逻辑**: Mock `shutil.rmtree`，验证 `clear_market_data` 是否正确过滤掉非目录文件（如 `.gitkeep`）。

### 5.2 集成测试
*   **Stub 验证**: 使用 `StubDataSource` 模拟返回 100 条历史数据，验证执行 `--init` 后，生成的 CSV 文件行数精确等于 100。
*   **故障转移**: 模拟主数据源失败，验证系统是否自动切换到次优数据源抓取历史数据。

### 5.3 冒烟测试
*   针对 A-Share 市场选择 2 只标的执行 `python main.py --init --days 5`，观察日志输出、交互确认过程以及最终 CSV 文件的物理存储结构。

## 6. 交互体验示例
```text
[WARNING] 检测到 --init 参数，将清空 ./data 下的所有市场数据目录！
[PROMPT] 是否确认执行? [y/N]: y
[INFO] 正在清理 ./data/A-Share ... 完成。
[INFO] 开始初始化历史数据 [Depth: 365 days]
[INFO] [A-Share] 处理 000001.SZ ... 成功 (242条)
[ERROR] [A-Share] 处理 600000.SH ... 失败 (API Limit), 跳过并继续
[INFO] === 初始化完成，成功: 1, 失败: 1 ===
```
