# A-Share/HK/US 收盘日K线获取系统 (Refactored)

基于 Python 的多市场股票收盘数据获取工具，支持 A 股、港股及美股市场。经过架构重构，现已全面支持异步并发抓取与标准领域模型。

## 核心特性

- **异步架构**：基于 `asyncio` 实现全链路异步化，支持多市场并发抓取，显著提升网络密集型任务效率。
- **工作流模式**：引入 `Workflows` 层，将业务逻辑（同步、初始化、计算）与入口解耦，结构清晰。
- **标准模型**：使用 `KlineData` 和 `MarketStatus` 标准模型，确保数据流转的类型安全与一致性。
- **存储抽象**：解耦存储引擎（`BaseStorage`），原生支持 CSV 扁平化存储，易于扩展至数据库。
- **频率控制**：内置异步频率限制器（RateLimiter），精准控制各数据源的 QPS。
- **多源限制**：支持 Futu, Tencent, AkShare, YFinance 等多数据源自动故障切换。

## 快速开始

### 依赖安装
```bash
pip install -r requirements.txt
```

### 常用命令

1. **查看市场状态**
   ```bash
   python -m src.main --status
   ```

2. **执行增量同步** (获取最新交易日数据)
   ```bash
   python -m src.main --run
   ```

3. **初始化历史数据** (默认 365 天)
   ```bash
   python -m src.main --init --days 365
   ```

4. **计算最新涨幅汇总**
   ```bash
   python -m src.main --calc-pct
   ```

## 项目结构
- `src/models/`: 标准化领域模型。
- `src/workflows/`: 业务工作流实现。
- `src/core/storage/`: 存储引擎抽象与实现。
- `src/data_sources/`: 异步封装的数据源管理器。
- `src/trading_calendar/`: 基于 `exchange_calendars` 的交易日历校验。

## 运行环境
- Python 3.10+
- 推荐配合 [FutuOpenD](https://www.futunn.com/download/open-api) 使用以获取更高质量的港美股数据。
