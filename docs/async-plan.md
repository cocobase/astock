# 异步非阻塞获取与请求频率控制设计方案 (async-plan.md)

## 1. 现状技术结构分析

目前系统采用典型的**同步阻塞式架构**：
- **调用链**：`main.py` -> `DataSourceManager` -> `BaseDataSource (Futu/Akshare/YFinance)`。
- **阻塞点**：每次网络请求（如 `ak.stock_zh_a_hist` 或 `yf.download`）都会导致整个进程挂起，直到数据返回或超时。
- **局限性**：无法在等待期间执行其他任务（如心跳维持、日志异步写入等），且难以精确控制请求频率（只能使用 `time.sleep`，这会进一步锁定进程）。

## 2. 设计目标：顺序非阻塞流 (Sequential Non-blocking Flow)

在保持数据获取逻辑顺序执行的基础上（符合大多数反爬虫要求），引入 `asyncio` 异步框架：
1.  **非阻塞等待**：将网络 I/O 等待交还给事件循环。
2.  **可配置频率控制**：在两次请求之间引入 `n` 秒的异步休眠，不阻塞系统响应。
3.  **兼容性**：由于 `akshare` 和 `yfinance` 等库是同步实现的，需通过线程池（Thread Pool）进行异步包装。

## 3. 核心配置调整 (`config/config.yaml`)

在 `global_settings` 中新增频率控制参数：

```yaml
global_settings:
  request_interval: 2  # 每次请求标的后的休眠秒数 (支持浮点数)
  max_concurrency: 1   # 默认顺序执行，设为 1 保证最严控速
```

## 4. 详细代码调整方案

### 4.1 数据源基类异步化抽象 (`src/data_sources/base.py`)
虽然底层库是同步的，但在管理器层面我们需要异步接口。
- **调整**：保持 `BaseDataSource` 接口简单，由管理器负责异步包装。

### 4.2 管理器改造 (`src/data_sources/manager.py`)
这是逻辑变更的核心。
- **引入 `asyncio`**：新增 `fetch_with_failover_async` 异步方法。
- **线程池包装**：使用 `asyncio.to_thread()` 调用同步的数据源方法，防止阻塞事件循环。
- **频率控制**：在方法内部或循环处执行 `await asyncio.sleep(interval)`。

### 4.3 接入层调整 (`src/main.py`)
- **入口改造**：将 `main()` 函数定义为 `async def main()`。
- **事件循环**：使用 `asyncio.run(main())` 启动。
- **流控执行**：
  ```python
  for code in codes:
      data = await manager.fetch_with_failover_async(priority, code, target_date)
      # 存储数据...
      await asyncio.sleep(global_settings.get("request_interval", 0))
  ```

## 5. 预期收益与评估

1.  **系统响应性**：在等待网络返回或休眠期间，主线程可以处理其他并发任务（如未来可能加入的 Web 监控接口）。
2.  **合规控速**：通过 `asyncio.sleep` 实现的控速比 `time.sleep` 更优雅，不会导致 CPU 资源的无效占用。
3.  **平滑扩展**：如果未来需要从“顺序获取”改为“多市场并发获取”，只需将 `for` 循环改为 `asyncio.gather` 即可，底层架构无需重构。

## 6. 风险提示
- **富途长连接**：`futu-api` 的 `OpenQuoteContext` 在异步环境下需要确保其回调和心跳不被事件循环阻塞。
- **库线程安全**：需确认 `akshare` 等库在多线程调用（`to_thread`）时的稳定性。
