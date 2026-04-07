# 重构方案 Phase 2：全面异步化与频率控制 (Async)

## 1. 目标
- **核心逻辑异步化**：将 `DataSourceManager` 和各个 `Workflow` 迁移至 `async/await` 架构。
- **并发性能提升**：通过异步等待，允许系统在等待网络返回时执行心跳维护、日志记录等。
- **精准频率控制**：引入 `RateLimiter` 替代 `time.sleep`，支持更精细的 QPS 控制。

## 2. 核心设计

### 2.1 异步改造策略
- **异步入口**: `main.py` -> `asyncio.run(main())`。
- **异步管理**: `DataSourceManager` 新增 `fetch_async_with_failover()`。
- **同步库包装**: 使用 `asyncio.to_thread()` 将 `akshare`, `yfinance` 等同步库调用桥接至线程池，防止阻塞事件循环。

### 2.2 频率限制器 (RateLimiter)
- 设计一个通用 `RateLimiter` 模块，可配置不同数据源的 QPS。
- 集成在 `fetch_..._async` 方法中，自动实现请求间的异步休眠。

### 2.3 异常容错
- 异步任务抛出异常时，通过 `try-except` 包裹，确保单次标的失败不崩溃整个事件循环。
- 支持异步重试逻辑。

## 3. 技术调整
- 配置文件新增 `request_interval`, `max_concurrency` 字段。
- 各个 `Workflow.run()` 变更为 `async def run()`。

## 4. 预期收益
1. 在网络延迟较大的情况下，多市场同步抓取的总耗时可减少 30% 以上。
2. 架构具备向并发获取（`asyncio.gather`）扩展的基础能力。
3. 解决富途长连接在长时间阻塞下载过程中可能导致的心跳超时风险。
