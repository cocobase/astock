import asyncio
from datetime import datetime
from loguru import logger
from .base import BaseWorkflow
from src.core.logger import log_detail


class SyncDailyWorkflow(BaseWorkflow):
    async def run(self, args):
        tasks = []
        for market_name, m_config in self.market_configs.items():
            tasks.append(self._process_market(market_name, m_config))
        
        # 并发处理各个市场
        await asyncio.gather(*tasks)

    async def _process_market(self, market_name, m_config):
        exchange_code = m_config.get("calendar")
        timezone = m_config.get("timezone")
        priority = m_config.get("priority", [])
        codes = m_config.get("codes", [])
        
        # 获取市场交易状态 (目前 calendar_checker 还是同步的，用 to_thread 包装)
        market_status = await asyncio.to_thread(self.calendar_checker.get_market_trading_status, market_name, exchange_code, timezone)
        target_date = datetime.strptime(market_status.last_trading_day, "%Y-%m-%d")
        date_str = target_date.strftime("%Y-%m-%d")

        logger.info(
            f"市场: {market_name} | 最后一个交易日: {market_status.last_trading_day} | "
            f"日历来源: {market_status.calendar_source}"
        )
            
        # 逐个标的处理（内部 manager 已经有频率限制锁）
        for code in codes:
            logger.info(f"开始处理标的: {code} ({market_name})")
            
            # 使用 async 版本的 fetch
            data = await self.manager.fetch_async_with_failover(priority, code, target_date)
            
            if data is not None and not data.empty:
                source_used = data.iloc[0]["source"]
                logger.info(f"标的 {code} 获取成功, 来源: {source_used}")
                # storage.save_data 涉及文件 IO，使用 to_thread
                await asyncio.to_thread(self.storage.save_data, data, market_name)
                log_detail(f"股票: {code} | 市场: {market_name} | 交易日期: {date_str} | 状态: 成功 | 来源: {source_used}")
            else:
                logger.error(f"标的 {code} 获取失败 (所有数据源均不可用)")
                log_detail(f"股票: {code} | 市场: {market_name} | 交易日期: {date_str} | 状态: 失败")
