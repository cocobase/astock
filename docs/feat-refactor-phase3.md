# 重构方案 Phase 3：领域模型化与存储抽象 (Models & Storage)

## 1. 目标
- **数据流标准化**：使用 Pydantic 或 dataclasses 定义标准模型，消除 pd.DataFrame 和 dict 在传递时的不确定性。
- **存储引擎解耦**：抽象 `BaseStorage` 接口，使系统能够轻松切换 CSV、SQLite 或数据库存储。
- **类型安全增强**：在整个项目推行类型提示 (Type Hinting)，提高 IDE 支持和编译期报错。

## 2. 核心设计

### 2.1 引入 `src/models/`
- **`KlineData`**: 标准化 OHLCV 字段，包含 `trade_date`, `stock_code`, `open`, `high`, `low`, `close`, `volume`, `amount`, `adj_type`, `source`, `fetch_time`。
- **`MarketStatus`**: 标准化市场状态信息，包括日历、交易所编码、时区和开市状态。

### 2.2 存储层重构
- **`BaseStorage`**: 定义存储接口，包括 `save_kline()`, `get_last_n_rows()`, `clear_all()`。
- **`CsvStorage`**: 修改为继承 `BaseStorage`，内部实现 CSV 写入逻辑。
- **[可选扩展] `SqliteStorage`**: 为未来可能的数据库方案提供参考实现。

### 2.3 流程流转
- 数据源 `fetch` 返回的是 `List[KlineData]` 模型列表，而非 DataFrame。
- 工作流 `Workflow` 处理模型对象，最终交给 `Storage` 持久化。

## 3. 预期目录结构
```text
src/
├── models/
│   ├── __init__.py
│   ├── kline.py          # KlineData
│   └── market.py         # MarketStatus
└── core/
    └── storage/
        ├── __init__.py
        ├── base.py       # BaseStorage
        └── csv_impl.py   # 原 CsvStorage 实现
```

## 4. 验收标准
1. 全项目核心函数均具备完善的 Type Hints。
2. 数据存储逻辑完全封装在 Storage 实现中，Workflow 不再关心文件路径细节。
3. 增加单元测试，验证 `KlineData` 模型的校验逻辑（如价格非负、日期格式合法等）。
