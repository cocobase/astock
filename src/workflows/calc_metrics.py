import asyncio
from loguru import logger
from .base import BaseWorkflow
from src.core.analyzer import DataAnalyzer


class CalcMetricsWorkflow(BaseWorkflow):
    async def run(self, args):
        logger.info("检测到 --calc-pct，执行最新涨幅计算任务 (Async Wrapper)")
        analyzer = DataAnalyzer(self.storage, self.config_loader)
        # 封装阻塞的同步计算任务
        await asyncio.to_thread(analyzer.calculate_pct_change)
