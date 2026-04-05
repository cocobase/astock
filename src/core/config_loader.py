import yaml
import os
from loguru import logger

class ConfigLoader:
    def __init__(self, config_path="config/config.yaml"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            logger.info(f"成功加载配置文件: {config_path}")

    def get_market_config(self, market_name):
        return self.config.get("market_configs", {}).get(market_name)

    def get_global_settings(self):
        return self.config.get("global_settings", {})

    def get_data_source_settings(self, source_name):
        return self.config.get("data_sources", {}).get(source_name)
