# astock 项目说明

## 1. 项目简介

`astock` 是一个面向 **A股 / 港股 / 美股** 的多源收盘日 K 线自动获取与持久化工具。

项目核心目标：
- **智能调度**：基于 `exchange_calendars` 自动判断各市场交易状态，仅在收盘后或非交易日执行数据补录。
- **高可靠性**：支持 `tencent`, `futu`, `yfinance`, `akshare` 等多数据源按优先级自动切换（Failover）。
- **历史回溯**：集成腾讯财经历史 K 线接口，支持全天候补录过去 320 天内的任意交易日数据。
- **数据标准化**：统一不同数据源的 OHLCV 字段、复权类型（支持 QFQ）及数值单位（A股自动手转股）。
- **本地持久化**：以 CSV 格式增量存储，自带去重逻辑。

---

## 2. 核心能力

### 2.1 市场状态判断
系统实时监控三大市场（A股、港股、美股）的交易日历：
- **自动定位**：准确计算“最后一个交易日”，无论当前是否处于交易时段。
- **时区感知**：完美处理美股与亚洲市场的时差问题。

### 2.2 多源数据引擎
| 数据源 | 覆盖市场 | 优势 | 备注 |
| :--- | :--- | :--- | :--- |
| **tencent** | A/HK/US | **推荐**。支持历史、前复权、自动识别美股后缀、响应极快。 | 历史接口缺失 Amount，采用 Close*Volume 估算。 |
| **futu** | HK | 官方 API，数据极其精准。 | 需本地运行 FutuOpenD 客户端。 |
| **yfinance** | US | 覆盖面广，原生支持前复权。 | 依赖网络环境。 |
| **akshare** | A | 备选源。 | - |

### 2.3 智能代码转换 (Symbol Transformer)
用户只需在配置中输入标准格式（如 `US.AAPL`, `SH.600519`），系统会自动处理：
- **A股**: `SH.600519` -> `sh600519`，并处理成交量“手”与“股”的转换。
- **港股**: `HK.00700` -> `hk00700`。
- **美股**: 自动匹配交易所后缀（如 `AAPL` -> `usAAPL.OQ`, `WMT` -> `usWMT.N`）。

### 2.4 数据存储逻辑
路径结构：`data/{market}/{year}/{market}_{code}_daily_kline.csv`
- **增量写入**：仅追加新数据，不破坏历史记录。
- **严格去重**：基于 `trade_date` 确保唯一性。

---

## 3. 项目结构

```text
astock/
├─ config/
│  └─ config.yaml                # 项目配置文件
├─ data/                         # CSV 数据存储目录
├─ docs/                         # 设计文档与参考资料
│  ├─ tencent-hist-migration-design.md # 腾讯历史接口迁移设计
│  └─ tencent_finance_api_reference.md # 腾讯 API 详细参考
├─ src/
│  ├─ main.py                    # 启动入口
│  ├─ core/
│  │  ├─ storage.py              # CSV 存储逻辑
│  │  └─ manager.py              # 数据源 Failover 调度
│  ├─ data_sources/
│  │  ├─ tencent_source.py       # 核心：腾讯财经多源接口 (NEW)
│  │  ├─ futu_source.py          # 富途牛牛接口
│  │  └─ yfinance_source.py      # Yahoo Finance 接口
│  └─ trading_calendar/
│     └─ checker.py              # 市场日历校验
└─ tests/
    ├─ test_tencent_pytest.py    # 腾讯接口覆盖测试
    └─ test_trading_calendar_checker.py # 日历逻辑测试
```

---

## 4. 快速开始

### 4.1 安装依赖
```bash
pip install -r requirements.txt
```
*注：本项目依赖 `pandas`, `requests`, `exchange_calendars`, `yfinance`, `futu-api` 等库。*

### 4.2 配置标的
编辑 `config/config.yaml`，在对应市场的 `codes` 列表中添加股票：
```yaml
market_configs:
  A-Share:
    codes: ["SH.600519", "SZ.000858"]
  US:
    codes: ["US.NVDA", "US.AAPL"]
```

### 4.3 运行任务

**查看市场闭市状态**：
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 src/main.py --status
```

**执行全量采集**：
```bash
python3 src/main.py --run
```

---

## 5. 测试验证

系统配备了严谨的测试套件，建议在发布或重大修改后运行：

**腾讯接口全覆盖测试 (A/HK/US/复权/降级)**：
```bash
pytest tests/test_tencent_pytest.py -v
```

**交易日历逻辑测试**：
```bash
pytest tests/test_trading_calendar_checker.py -v
```

---

## 6. 版本记录 (Roadmap)
- **V1.0 (Current)**: 
    - [x] 实现基于腾讯财经的历史 K 线补录。
    - [x] 支持 A/HK/US 多市场日历感知。
    - [x] 建立完善的 Failover 数据源调度机制。
    - [x] 实现美股交易所后缀自动识别逻辑。
- **Future**:
    - [ ] 集成飞书/钉钉推送通知。
    - [ ] 增加环境变量支持（`.env`）以剥离敏感配置。
    - [ ] 增加 Web 监控看板。
