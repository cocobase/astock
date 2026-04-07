from datetime import datetime
from loguru import logger
from .base import BaseWorkflow
from src.core.logger import log_detail


class SyncDailyWorkflow(BaseWorkflow):
    def run(self, args):
        for market_name, m_config in self.market_configs.items():
            exchange_code = m_config.get("calendar")
            timezone = m_config.get("timezone")
            priority = m_config.get("priority", [])
            codes = m_config.get("codes", [])
            
            # 获取市场交易状态
            market_status = self.calendar_checker.get_market_trading_status(exchange_code, timezone)
            target_date = datetime.strptime(market_status.last_trading_day, "%Y-%m-%d")
            date_str = target_date.strftime("%Y-%m-%d")

            logger.info(
                f"市场: {market_name} | 最后一个交易日: {market_status.last_trading_day} | "
                f"日历来源: {market_status.calendar_source}"
            )
                
            # 执行数据获取与持久化
            for code in codes:
                logger.info(f"开始处理标的: {code} ({market_name})")
                
                # 按优先级顺序获取数据
                data = self.manager.fetch_with_failover(priority, code, target_date)
                
                if data is not None and not data.empty:
                    source_used = data.iloc[0]["source"]
                    logger.info(f"标的 {code} 获取成功, 来源: {source_used}")
                    self.storage.save_data(data, market_name)
                    log_detail(f"股票: {code} | 市场: {market_name} | 交易日期: {date_str} | 状态: 成功 | 来源: {source_used}")
                else:
                    logger.error(f"标的 {code} 获取失败 (所有数据源均不可用)")
                    log_detail(f"股票: {code} | 市场: {market_name} | 交易日期: {date_str} | 状态: 失败")
