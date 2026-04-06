# TencentDataSource 迁移至历史 K 线接口设计文档

## 1. 设计动机
为了解决 `TencentDataSource` 无法获取历史数据的问题，提升系统在非交易时段运行时的鲁棒性，计划将底层 API 从“实时快照”切换为“历史 K 线”接口。

## 2. 架构变更对比

| 维度 | 现状 (Snapshot API) | 目标 (History API) |
| :--- | :--- | :--- |
| **API Endpoint** | `qt.gtimg.cn/q=...` | `web.ifzq.gtimg.cn/appstock/.../get` |
| **数据格式** | 文本字符串 (Tilde 分割) | JSON 结构化数据 |
| **复权支持** | 仅不复权 | 原生支持 qfq / hfq |
| **日期限制** | 仅支持“今天”或“最后交易日” | 支持指定范围的历史追溯 |
| **错误处理** | 匹配 `v_pv_none_match` | 检查 JSON 中的 `code` 字段 |

## 3. 详细设计方案

### 3.1 字段映射逻辑
腾讯历史接口返回的日线数据为数组形式，初步预估映射关系如下：
*   `data[0]` (Date) -> `trade_date`
*   `data[1]` (Open) -> `open`
*   `data[2]` (Close) -> `close`
*   `data[3]` (High) -> `high`
*   `data[4]` (Low) -> `low`
*   `data[5]` (Volume) -> `volume`
*   `data[6]` (Amount) -> `amount` (需注意 A 股单位通常为万元)

### 3.2 逻辑重构步骤
1.  **新增配置支持**: 在 `fetch_daily_kline` 中接收复权类型参数，动态构造 `adj_type`。
2.  **代码实现**:
    *   实现 `_get_hist_url(stock_code, date)` 辅助函数。
    *   使用 `requests.get().json()` 获取并校验返回状态。
    *   解析 `['data'][symbol]['day']` 或 `['data'][symbol]['qfqday']` 下的列表。
3.  **健壮性处理**:
    *   如果请求的是“今天”，且历史接口尚未更新，则尝试自动降级到快照接口（可选）。
    *   增加对 JSON 解析异常的捕获。

### 3.3 预期收益
*   **全天候可用**: 系统可在任意时间启动，准确补录过去 1-320 天的数据。
*   **数据一致性**: 支持前复权，使腾讯数据源可以与 `yfinance` 互为完美备选。

## 4. 迁移风险与规避
*   **接口变动**: 历史接口为腾讯 Web 端内部接口，稳定性可能略低于行情网关。*规避：保留原快照解析逻辑作为私有备份。*
*   **解析性能**: JSON 解析比字符串分割略慢。*规避：在 Phase 1 阶段标的数量较少时忽略不计。*
