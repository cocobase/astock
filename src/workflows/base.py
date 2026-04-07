from abc import ABC, abstractmethod
import asyncio
from loguru import logger
from src.core.config_loader import ConfigLoader
from src.core.storage import CsvStorage
from src.trading_calendar.checker import CalendarChecker
from src.data_sources.manager import DataSourceManager
from src.data_sources.futu_source import FutuDataSource
from src.data_sources.akshare_source import AkshareDataSource
from src.data_sources.yfinance_source import YFinanceDataSource
from src.data_sources.tencent_source import TencentDataSource


class BaseWorkflow(ABC):
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.global_settings = config_loader.get_global_settings()
        self.market_configs = config_loader.config.get("market_configs", {})
        
        self.storage = None
        self.calendar_checker = None
        self.manager = None
        self.futu_source = None

    async def setup(self):
        """[Async] 初始化通用组件"""
        self.storage = CsvStorage(root_path=self.global_settings.get("storage_root", "./data"))
        self.calendar_checker = CalendarChecker()
        
        # 初始化数据源管理器
        self.manager = DataSourceManager(
            retry_count=self.global_settings.get("retry_count", 2),
            timeout=self.global_settings.get("timeout", 10),
            request_interval=self.global_settings.get("request_interval", 0.5)
        )
        
        # 注册数据源 (同步方法)
        self._setup_data_sources()

    def _setup_data_sources(self):
        # Futu
        futu_cfg = self.config_loader.get_data_source_settings("futu") or {}
        self.futu_source = FutuDataSource(
            host=futu_cfg.get("host", "127.0.0.1"),
            port=futu_cfg.get("port", 11111)
        )
        self.manager.register_source(self.futu_source)
        
        # AKShare
        self.manager.register_source(AkshareDataSource())

        # yfinance & Tencent
        yf_cfg = self.config_loader.get_data_source_settings("yfinance") or {}
        proxy = yf_cfg.get("proxy")
        self.manager.register_source(YFinanceDataSource(proxy=proxy))
        self.manager.register_source(TencentDataSource(proxy=proxy))

    async def cleanup(self):
        """[Async] 清理资源"""
        if self.futu_source:
            # 同样封装同步的 close
            await asyncio.to_thread(self.futu_source.close)
        logger.info("工作流资源清理完成")

    @abstractmethod
    async def run(self, args):
        """[Async] 执行主逻辑"""
        pass
