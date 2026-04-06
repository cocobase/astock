# astock 项目说明

## 1. 项目简介

`astock` 是一个面向 **A股 / 港股 / 美股** 的多源收盘日 K 线自动获取、初始化与持久化工具。

项目核心目标：
- **全生命周期管理**：支持从 **一键初始化历史数据** 到 **每日增量补录** 的完整数据闭环。
- **智能调度**：基于 `exchange_calendars` 自动判断各市场交易状态，仅在收盘后或非交易日执行任务。
- **高性能批量抓取**：针对初始化场景优化，利用 `tencent`, `akshare`, `yfinance`, `futu` 的历史批量接口，效率比传统循环抓取提升数倍。
- **高可靠性**：支持多数据源按优先级自动切换（Failover），确保数据获取不中断。
- **数据标准化**：强制执行 **STANDARD_FIELDS** 列排序校验（OHLCV 顺序），确保不同来源数据落盘格式严格统一。
- **本地持久化**：以 CSV 格式存储，按年/市场分目录管理，自带增量去重逻辑。

---

## 2. 核心能力

### 2.1 历史数据初始化 (`--init`)
为新项目或新标的一键补全历史 K 线：
- **深度自定义**：支持通过 `--days` 参数指定回溯天数（默认 365 天）。
- **精准清理**：初始化前自动清理旧数据目录，保留非数据配置文件（如 `.gitkeep`）。
- **交互安全**：强制执行交互式确认（y/N），防止生产环境误删。

### 2.2 市场状态判断
系统实时监控三大市场（XSHG, XHKG, XNYS）的交易日历：
- **时区感知**：自动处理美股与亚洲市场的时差，确保在正确的市场时间点触发抓取。
- **日历回溯**：通过 `get_recent_trading_days` 准确识别过去 N 个真实的交易日期。

### 2.3 多源数据引擎
| 数据源 | 覆盖市场 | 优势 | 备注 |
| :--- | :--- | :--- | :--- |
| **tencent** | A/HK/US | **推荐**。支持范围查询、响应极快、自动识别美股后缀。 | 历史接口采用 Close*Volume 估算 Amount。 |
| **futu** | HK/A/US | 官方 API，数据极其精准。 | 需本地运行 FutuOpenD 客户端。 |
| **yfinance** | US | 覆盖面广，原生支持前复权。 | 依赖网络环境，支持代理配置。 |
| **akshare** | A | 国内开源首选，接口丰富。 | - |

### 2.4 数据质量保障
- **强制列排序**：无论数据源返回的字典顺序如何，落盘前均强制重排为 `trade_date, stock_code, open, high, low, close, volume, amount...`。
- **字段校验**：保存前自动检查必要字段，缺失关键数据将安全报错并跳过，防止污染磁盘文件。

---

## 3. 项目结构

```text
astock/
├─ config/
│  └─ config.yaml                # 项目配置文件
├─ data/                         # CSV 数据存储目录
├─ docs/                         # 设计文档
│  ├─ feat-init-data-v01.md      # 初始化功能设计方案 (NEW)
│  └─ tencent_finance_api_reference.md # 腾讯 API 参考
├─ src/
│  ├─ main.py                    # 启动入口 (支持 --run, --init, --status)
│  ├─ core/
│  │  ├─ storage.py              # CSV 存储与列排序校验
│  │  └─ manager.py              # 批量历史/单日 Failover 调度
│  ├─ data_sources/              # 各类数据源适配器
│  └─ trading_calendar/          # 市场日历校验
└─ tests/
    ├─ test_init_workflow.py     # 初始化全流程集成测试 (NEW)
    ├─ test_recent_days.py       # 交易日回溯逻辑测试 (NEW)
    └─ test_tencent_pytest.py    # 腾讯接口覆盖测试
```

---

## 4. 快速开始

### 4.1 安装依赖
```bash
pip install -r requirements.txt
```

### 4.2 运行任务

**1. 初始化历史数据（首次使用或增加新标的时）**：
```bash
# 初始化过去 1 年的数据（会清空原有数据目录，需确认）
python3 src/main.py --init --days 365
```

**2. 执行每日增量采集（建议放入 Crontab）**：
```bash
# 仅下载最后一个交易日的最新数据
python3 src/main.py --run
```

**3. 查看各市场当前状态**：
```bash
python3 src/main.py --status
```

---

## 5. 测试验证

**初始化全流程模拟测试**：
```bash
python3 tests/test_init_workflow.py
```

**腾讯接口全覆盖测试**：
```bash
pytest tests/test_tencent_pytest.py -v
```

---

## 6. 版本记录 (Roadmap)
- **V1.1 (Current)**: 
    - [x] 实现 `--init` 历史数据一键初始化。
    - [x] 全面支持数据源历史批量抓取接口。
    - [x] 存储层强制执行标准列顺序（OHLCV）与字段校验。
    - [x] 优化 `CsvStorage` 大批量数据保存性能。
- **V1.0**: 
    - [x] 实现基于腾讯财经的历史 K 线增量补录。
    - [x] 建立 Failover 数据源调度机制。
- **Future**:
    - [ ] 集成飞书/钉钉推送通知。
    - [ ] 增加 Web 监控看板。
