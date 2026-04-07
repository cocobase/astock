from loguru import logger
from .base import BaseWorkflow
from src.core.analyzer import DataAnalyzer


class CalcMetricsWorkflow(BaseWorkflow):
    def run(self, args):
        logger.info("检测到 --calc-pct，执行最新涨幅计算任务")
        analyzer = DataAnalyzer(self.storage, self.config_loader)
        analyzer.calculate_pct_change()
