import argparse
from datetime import datetime
from src.core.config_loader import ConfigLoader
from src.core.logger import setup_logger, log_detail
from src.trading_calendar.checker import CalendarChecker
from src.data_sources.manager import DataSourceManager
from src.data_sources.base import StubDataSource
from src.data_sources.futu_source import FutuDataSource
from src.data_sources.akshare_source import AkshareDataSource
from src.data_sources.yfinance_source import YFinanceDataSource
from src.core.storage import CsvStorage
from src.constants import Market
from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser(description="多市场收盘日K获取系统")
    parser.add_argument("--status", action="store_true", help="只显示所有市场状态后结束")
    parser.add_argument("--run", action="store_true", help="执行下载任务")
    args = parser.parse_args()

    if args.status and args.run:
        parser.error("--status 与 --run 不能同时使用")
    if not args.status and not args.run:
        parser.error("必须指定 --status 或 --run")

    return args


def format_market_status_overview(market_status_overview: dict) -> str:
    if not market_status_overview:
        return "三大市场状态总览:\n  (无可用市场配置)"

    lines = ["三大市场状态总览:"]
    for market_name, status in market_status_overview.items():
        lines.extend([
            f"[{market_name}]",
            f"  交易所: {status.get('exchange_code', '')}",
            f"  时区: {status.get('timezone', '')}",
            f"  当前时间: {status.get('market_now', '')}",
            f"  当前市场日期: {status.get('market_date', '')}",
            f"  今日是否交易日: {status.get('is_trading_day_today', '')}",
            f"  当日交易时段是否结束: {status.get('is_current_session_closed', '')}",
            f"  最后一个交易日: {status.get('last_trading_day', '')}",
            f"  日历来源: {status.get('calendar_source', '')}",
            ""
        ])
    return "\n".join(lines).rstrip()


def main():
    # 1. 初始化配置与日志
    config_loader = ConfigLoader()
    global_settings = config_loader.get_global_settings()
    setup_logger(
        log_root=global_settings.get("log_root", "./logs"),
        rotation=global_settings.get("log_rotation", "00:00")
    )
    
    args = parse_args()

    logger.info("=== 多市场收盘日K获取系统启动 (Phase 1 真实接入与持久化) ===")
    
    calendar_checker = CalendarChecker()

    # 2. 启动时打印市场状态总览
    market_configs = config_loader.config.get("market_configs", {})
    market_status_overview = calendar_checker.get_all_market_statuses(market_configs)
    logger.info("\n" + format_market_status_overview(market_status_overview))

    if args.status:
        logger.info("检测到 --status，仅输出市场状态，不执行下载")
        logger.info("=== 任务运行结束 ===")
        return

    storage = CsvStorage(root_path=global_settings.get("storage_root", "./data"))
    
    # 3. 初始化数据源管理器
    manager = DataSourceManager(
        retry_count=global_settings.get("retry_count", 2),
        timeout=global_settings.get("timeout", 10)
    )
    
    # 注册真实数据源 (Futu)
    futu_cfg = config_loader.get_data_source_settings("futu") or {}
    futu_source = FutuDataSource(
        host=futu_cfg.get("host", "127.0.0.1"),
        port=futu_cfg.get("port", 11111)
    )
    manager.register_source(futu_source)
    
    # 注册真实数据源 (AKShare)
    manager.register_source(AkshareDataSource())

    # 注册真实数据源 (yfinance)
    yf_cfg = config_loader.get_data_source_settings("yfinance") or {}
    yf_source = YFinanceDataSource(proxy=yf_cfg.get("proxy"))
    manager.register_source(yf_source)
    
    # 4. 按市场迭代执行
    for market_name, m_config in market_configs.items():
        exchange_code = m_config.get("calendar")
        timezone = m_config.get("timezone")
        priority = m_config.get("priority", [])
        codes = m_config.get("codes", [])
        
        # 获取市场交易状态与最后一个交易日
        market_status = calendar_checker.get_market_trading_status(exchange_code, timezone)
        target_date = datetime.strptime(market_status.last_trading_day, "%Y-%m-%d")
        date_str = target_date.strftime("%Y-%m-%d")

        logger.info(
            f"市场: {market_name} | 市场当前时间: {market_status.market_now} | "
            f"今日是否交易日: {market_status.is_trading_day_today} | "
            f"当日交易时段是否结束: {market_status.is_current_session_closed} | "
            f"最后一个交易日: {market_status.last_trading_day} | "
            f"日历来源: {market_status.calendar_source}"
        )
            
        # 5. 执行数据获取与持久化
        for code in codes:
            logger.info(f"开始处理标的: {code} ({market_name})")
            
            # 按优先级顺序获取数据
            data = manager.fetch_with_failover(priority, code, target_date)
            
            if data is not None and not data.empty:
                source_used = data.iloc[0]["source"]
                logger.info(f"标的 {code} 获取成功, 来源: {source_used}")
                
                # 持久化落地
                storage.save_data(data, market_name)
                
                log_detail(
                    f"执行时间: {datetime.now()} | 股票: {code} | 市场: {market_name} | "
                    f"交易日期: {date_str} | 今日是否交易日: {market_status.is_trading_day_today} | "
                    f"当日交易时段是否结束: {market_status.is_current_session_closed} | "
                    f"最后一个交易日: {market_status.last_trading_day} | 日历来源: {market_status.calendar_source} | "
                    f"状态: 成功 | 来源: {source_used}"
                )
            else:
                logger.error(f"标的 {code} 获取失败 (所有数据源均不可用)")
                log_detail(
                    f"执行时间: {datetime.now()} | 股票: {code} | 市场: {market_name} | "
                    f"交易日期: {date_str} | 今日是否交易日: {market_status.is_trading_day_today} | "
                    f"当日交易时段是否结束: {market_status.is_current_session_closed} | "
                    f"最后一个交易日: {market_status.last_trading_day} | 日历来源: {market_status.calendar_source} | "
                    f"状态: 失败 | 原因: 链路所有数据源重试后均失败"
                )

    # 6. 清理资源
    futu_source.close()
    logger.info("=== 任务运行结束 ===")

if __name__ == "__main__":
    main()
