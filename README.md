# astock 项目说明

## 1. 项目简介

`astock` 是一个面向 **A股 / 港股 / 美股** 的收盘日 K 线自动获取工具。

项目目标是：

- 按市场交易日历判断是否应执行下载
- 只获取 **当前最后一个已完成交易日** 的日 K 数据
- 支持多数据源按优先级自动切换
- 将结果标准化后落地到 CSV
- 保留完整运行日志与下载明细，便于追溯

当前已支持：

- A股
- 港股
- 美股

---

## 2. 当前核心能力

### 2.1 市场状态判断

基于 `exchange_calendars` 判断各市场当前状态，包括：

- 今日是否为交易日
- 当前交易时段是否已经结束
- 当前最后一个交易日日期

当前规则：

- 如果今天是交易日且 **已收盘**，最后一个交易日 = 今天
- 如果今天是交易日但 **未收盘**，最后一个交易日 = 上一个交易日
- 如果今天 **不是交易日**，最后一个交易日 = 上一个交易日

项目启动时可直接输出三大市场状态总览。

### 2.2 多数据源获取

已接入或预留的数据源：

- `futu`
- `akshare`
- `yfinance`
- `tushare`（配置已预留，当前主流程未实际注册）

各市场支持通过配置设置优先级，单个数据源失败后会自动重试，再切换到下一个数据源。

### 2.3 数据标准化与存储

所有数据源返回的数据会统一为标准字段后写入 CSV。

默认存储路径结构：

```text
data/{market}/{year}/{market}_{code}_daily_kline.csv
```

例如：

```text
data/A-Share/2026/A-Share_SH_600519_daily_kline.csv
```

写入策略：

- 增量追加
- 按 `stock_code + trade_date` 去重
- 不覆盖已有有效记录

### 2.4 日志能力

系统使用双日志：

- `logs/run.log`：系统运行日志
- `logs/download_detail.log`：逐标的下载明细日志

下载明细日志中会记录：

- 执行时间
- 股票代码
- 市场
- 交易日期
- 今日是否交易日
- 当日交易时段是否结束
- 最后一个交易日
- 日历来源
- 成功/失败状态
- 成功时的数据源
- 失败原因

---

## 3. 当前项目结构

```text
astock/
├─ config/
│  └─ config.yaml                # 项目配置
├─ data/                         # CSV 数据落地目录
├─ docs/
│  ├─ README.md                  # 本文档
│  ├─ market-prd.md              # 需求文档
│  ├─ async-plan.md              # 异步化规划
│  └─ phrase1.md
├─ logs/                         # 运行日志与明细日志
├─ src/
│  ├─ main.py                    # 程序入口
│  ├─ constants.py               # 枚举与字段常量
│  ├─ core/
│  │  ├─ config_loader.py        # 配置加载
│  │  ├─ logger.py               # 日志初始化
│  │  └─ storage.py              # CSV 存储
│  ├─ data_sources/
│  │  ├─ base.py                 # 数据源抽象基类
│  │  ├─ manager.py              # 数据源调度与 failover
│  │  ├─ futu_source.py          # 富途数据源
│  │  ├─ akshare_source.py       # AKShare 数据源
│  │  └─ yfinance_source.py      # yfinance 数据源
│  └─ trading_calendar/
│     └─ checker.py              # 市场交易日历与市场状态判断
└─ tests/                        # 测试代码
```

---

## 4. 关键模块说明

### `src/main.py`
程序主入口，负责：

- 解析命令行参数
- 初始化配置与日志
- 输出市场状态总览
- 在 `--run` 模式下执行下载流程

### `src/trading_calendar/checker.py`
交易日历核心模块，负责：

- 加载并缓存交易所日历
- 判断某天是否交易日
- 判断交易日是否已收盘
- 计算当前最后一个交易日
- 一次性返回所有市场状态

这是“市场状态判断”最合适的归属位置。

### `src/data_sources/manager.py`
数据源编排模块，负责：

- 按优先级调用数据源
- 自动重试
- 自动切换故障数据源

### `src/core/storage.py`
CSV 落盘模块，负责：

- 生成目标文件路径
- 增量写入
- 去重

---

## 5. 配置说明

主配置文件：`config/config.yaml`

当前主要配置项：

### 5.1 市场配置

每个市场包含：

- `calendar`：交易所日历编码
- `timezone`：市场时区
- `priority`：数据源优先级
- `codes`：标的列表

当前默认配置：

- A股：`XSHG` / `Asia/Shanghai`
- 港股：`XHKG` / `Asia/Hong_Kong`
- 美股：`XNYS` / `America/New_York`

### 5.2 数据源配置

包括：

- `futu.host`
- `futu.port`
- `tushare.token`
- `yfinance.proxy`

### 5.3 全局配置

包括：

- `retry_count`
- `timeout`
- `log_rotation`
- `storage_root`
- `log_root`
- `default_adj_type`

---

## 6. 命令行使用方式

当前入口支持两个模式：

### 6.1 仅查看市场状态

```bash
python -m src.main --status
```

作用：

- 输出 A股 / 港股 / 美股 的当前状态总览
- 不执行任何下载
- 返回状态信息如下：
[US]
  交易所: XNYS
  时区: America/New_York
  当前时间: 2026-04-03 10:14:50-0400
  当前市场日期: 2026-04-03
  今日是否交易日: False
  当日交易时段是否结束: True
  最后一个交易日: 2026-04-02
  日历来源: exchange_calendars

### 6.2 执行下载任务

```bash
python -m src.main --run
```

作用：

- 输出市场状态总览
- 然后进入逐市场、逐标的下载流程

### 6.3 参数约束

- `--status` 与 `--run` 不能同时使用
- 必须显式指定其中一个参数

---

## 7. 安装依赖

当前 `requirements.txt` 包含：

- `exchange-calendars>=4.0.0`
- `pytz`
- `pyyaml`
- `loguru`
- `pandas`
- `pytest`
- `freezegun`
- `futu-api`

建议使用虚拟环境安装：

```bash
pip install -r requirements.txt
```

> 说明：如果需要使用港股/美股或富途数据源，请确保本机环境与网络条件满足对应依赖要求。

---

## 8. 当前已实现的市场状态输出

项目现在支持启动时输出“三大市场状态总览”，字段包括：

- 交易所
- 时区
- 当前时间
- 当前市场日期
- 今日是否交易日
- 当日交易时段是否结束
- 最后一个交易日
- 日历来源

这部分能力主要用于：

- 下载前判断是否应抓取今天数据
- 快速确认各市场当前状态
- 作为后续接口化/监控化输出基础

---

## 9. 测试现状

当前已补充交易日历相关测试，覆盖以下场景：

- 今天是交易日且已收盘
- 今天是交易日但未收盘
- 今天不是交易日
- 一次性获取多个市场状态

可执行：

```bash
pytest -q tests/test_trading_calendar_checker.py
```

---

## 10. 已知现状与后续可优化项

### 已知现状

- `main.py` 使用 `python -m src.main ...` 启动更稳妥
- `tushare` 目前仅在配置中预留，尚未真正注册到主流程
- 部分数据源在不同网络环境下稳定性会有差异
- CSV 存储目前是单文件逐次读取去重，数据量大后可继续优化

### 后续建议

- 增加数据源健康检查与启动前预检
- 增加更友好的状态展示（如中文“是/否”“已结束/未结束”）
- 将市场状态输出封装为 API 或 CLI 子命令
- 增加历史补录能力
- 增加更完整的单元测试与集成测试

---

## 11. 相关文档

- `docs/market-prd.md`：需求说明
- `docs/async-plan.md`：异步化规划
- `config/config.yaml`：运行配置
- `src/trading_calendar/checker.py`：市场状态核心逻辑
- `src/main.py`：程序入口
