# 阶段 1：富途 OpenAPI 接入与 CSV 持久化实现

## 1. 目标
- **真实数据接入**：实现 `FutuDataSource`，通过富途 OpenAPI 获取 A/港/美股收盘日K数据。
- **持久化存储**：实现 `CsvStorage` 模块，支持按市场/年份自动分层存储，并具备增量去重功能。
- **流程整合**：`main.py` 能够调度真实数据源并将结果安全落地为 CSV 文件。

## 2. 技术设计

### 2.1 FutuDataSource 类 (`src/data_sources/futu_source.py`)
- **连接管理**：封装 `OpenQuoteContext`，在初始化时尝试连接本地 `FutuOpenD`。
- **数据获取**：调用 `get_history_kline` 接口，支持前复权 (qfq)。
- **字段转换**：将富途原始 DataFrame 转换为系统标准的 `KlineFields` 格式。
- **健壮性**：实现 `health_check` 探测网关状态，优雅处理连接异常。

### 2.2 CsvStorage 类 (`src/core/storage.py`)
- **目录规则**：`data/{market}/{year}/{market}_{code}_daily_kline.csv`。
- **增量逻辑**：
    - 读取已有 CSV 的最后一行日期。
    - 仅当新数据日期晚于已有日期时执行追加。
    - 自动处理表头创建。
- **安全性**：确保写入前目标目录已存在。

### 2.3 流程更新 (`src/main.py`)
- 初始化 `FutuDataSource` 并作为主数据源注册。
- 在数据获取成功后，调用 `CsvStorage.save_data()` 执行落地。
- 保留 `StubDataSource` 作为备用或测试占位。

## 3. 验证方案 (Testing)
1. **连接测试**：验证 `health_check` 是否能检测到 `FutuOpenD` 的启停。
2. **落地验证**：检查 `data/` 目录结构是否符合 `A-Share/2026/...` 的层级。
3. **去重验证**：重复运行脚本，确认 CSV 文件大小不再增长。

## 4. 依赖项
- `futu-api`: 富途官方 SDK。
