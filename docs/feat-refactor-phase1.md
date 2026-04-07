# 重构方案 Phase 1：架构解耦与业务编排化 (Workflows)

## 1. 目标
- **瘦身 `main.py`**：将其职责缩减为仅处理 CLI 参数解析和全局初始化。
- **引入工作流层**：在 `src/workflows/` 下实现具体的业务逻辑，提高代码复用性和可维护性。
- **标准化任务执行**：统一不同模式（Init, Run, Calc）的启动与异常处理流程。

## 2. 核心设计

### 2.1 引入 `BaseWorkflow` 抽象基类
定义所有业务流程的通用接口：
- `run()`: 执行主逻辑。
- `setup()`: 初始化所需的组件（Storage, Manager 等）。

### 2.2 具体工作流实现
1.  **`SyncDailyWorkflow`**: 对应原 `--run` 逻辑。负责检查日历、循环标的、获取增量数据并保存。
2.  **`InitHistoryWorkflow`**: 对应原 `--init` 逻辑。负责清理目录、计算历史区间、批量抓取。
3.  **`CalcMetricsWorkflow`**: 对应原 `--calc-pct` 逻辑。封装 `DataAnalyzer` 的调用过程。

### 2.3 `main.py` 改造
- 移除所有硬编码的业务逻辑判断。
- 根据 CLI 参数实例化对应的 Workflow 类并运行。

## 3. 预期目录结构
```text
src/
├── main.py
└── workflows/
    ├── __init__.py
    ├── base.py           # BaseWorkflow
    ├── sync_daily.py     # 增量同步流
    ├── init_history.py    # 初始化历史流
    └── calc_metrics.py    # 指标计算流
```

## 4. 验收标准
1. `main.py` 代码行数显著减少（预计减少 60% 以上）。
2. 各个模式的功能与重构前完全一致。
3. 新增业务模式只需在 `workflows/` 下增加新文件，无需大幅改动 `main.py`。
