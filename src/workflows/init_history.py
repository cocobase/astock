import asyncio
from loguru import logger
from .base import BaseWorkflow


class InitHistoryWorkflow(BaseWorkflow):
    async def run(self, args):
        # input 是阻塞的，用 to_thread
        confirm = await asyncio.to_thread(input, "[WARNING] 此操作将清空 ./data 目录下所有市场数据！是否确认? [y/N]: ")
        if confirm.lower() != 'y':
            logger.info("用户取消初始化。")
            return
            
        logger.warning("正在清理现有数据目录...")
        await asyncio.to_thread(self.storage.clear_market_data)

        # 这里使用并发处理各个市场
        tasks = [self._process_market_init(market_name, m_config, args.days) 
                 for market_name, m_config in self.market_configs.items()]
        await asyncio.gather(*tasks)

    async def _process_market_init(self, market_name, m_config, days):
        exchange_code = m_config.get("calendar")
        priority = m_config.get("priority", [])
        codes = m_config.get("codes", [])
        
        # 初始化逻辑：获取最近 N 个交易日
        logger.info(f"开始初始化市场: {market_name} (深度: {days} 天)")
        trading_days = await asyncio.to_thread(self.calendar_checker.get_recent_trading_days, exchange_code, days)
        if not trading_days:
            logger.error(f"无法获取市场 {market_name} 的交易日列表，跳过")
            return
        
        start_date = trading_days[0]
        end_date = trading_days[-1]
        logger.info(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        success_count = 0
        fail_count = 0
        
        for code in codes:
            logger.info(f"[{market_name}] 异步初始化标的: {code}")
            # 使用异步 fetch
            data = await self.manager.fetch_historical_async_with_failover(priority, code, start_date, end_date)
            
            if data is not None and not data.empty:
                await asyncio.to_thread(self.storage.save_data, data, market_name)
                success_count += 1
            else:
                logger.error(f"标的 {code} 初始化失败")
                fail_count += 1
        
        logger.info(f"市场 {market_name} 初始化完成: 成功 {success_count}, 失败 {fail_count}")
