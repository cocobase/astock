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
from src.data_sources.tencent_source import TencentDataSource
from src.core.storage import CsvStorage
from src.core.analyzer import DataAnalyzer
from src.constants import Market
from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser(description="多市场收盘日K获取系统")
    parser.add_argument("--status", action="store_true", help="只显示所有市场状态后结束")
    parser.add_argument("--run", action="store_true", help="执行增量下载任务")
    parser.add_argument("--init", action="store_true", help="初始化历史K线数据（会清空现有数据）")
    parser.add_argument("--days", type=int, default=365, help="初始化历史天数，默认365天")
    parser.add_argument("--calc-pct", action="store_true", help="计算本地数据的最新涨幅并汇总导出")
    args = parser.parse_args()

    active_modes = [args.status, args.run, args.init, args.calc_pct]
    if sum(active_modes) > 1:
        parser.error("--status, --run, --init, --calc-pct 不能同时使用")
    if sum(active_modes) == 0:
        parser.error("必须指定 --status, --run, --init 或 --calc-pct")

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
    
    if args.init:
        confirm = input("[WARNING] 此操作将清空 ./data 目录下所有市场数据！是否确认? [y/N]: ")
        if confirm.lower() != 'y':
            logger.info("用户取消初始化。")
            return
        logger.warning("正在清理现有数据目录...")
        storage.clear_market_data()

    if args.calc_pct:
        logger.info("检测到 --calc-pct，执行最新涨幅计算任务")
        analyzer = DataAnalyzer(storage, config_loader)
        analyzer.calculate_pct_change()
        logger.info("=== 任务运行结束 ===")
        return

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

    # 注册真实数据源 (Tencent)
    manager.register_source(TencentDataSource(proxy=yf_cfg.get("proxy")))
    
    # 4. 按市场迭代执行
    for market_name, m_config in market_configs.items():
        exchange_code = m_config.get("calendar")
        timezone = m_config.get("timezone")
        priority = m_config.get("priority", [])
        codes = m_config.get("codes", [])
        
        # 获取市场交易状态
        market_status = calendar_checker.get_market_trading_status(exchange_code, timezone)
        
        if args.init:
            # 初始化逻辑：获取最近 N 个交易日作为范围
            logger.info(f"开始初始化市场: {market_name} (深度: {args.days} 天)")
            trading_days = calendar_checker.get_recent_trading_days(exchange_code, args.days)
            if not trading_days:
                logger.error(f"无法获取市场 {market_name} 的交易日列表，跳过")
                continue
            
            start_date = trading_days[0]
            end_date = trading_days[-1]
            logger.info(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            
            success_count = 0
            fail_count = 0
            
            for code in codes:
                logger.info(f"[{market_name}] 初始化标的: {code}")
                data = manager.fetch_historical_with_failover(priority, code, start_date, end_date)
                
                if data is not None and not data.empty:
                    storage.save_data(data, market_name)
                    success_count += 1
                else:
                    logger.error(f"标的 {code} 初始化失败")
                    fail_count += 1
            
            logger.info(f"市场 {market_name} 初始化完成: 成功 {success_count}, 失败 {fail_count}")

        else:
            # 增量运行逻辑 (--run)
            target_date = datetime.strptime(market_status.last_trading_day, "%Y-%m-%d")
            date_str = target_date.strftime("%Y-%m-%d")

            logger.info(
                f"市场: {market_name} | 最后一个交易日: {market_status.last_trading_day} | "
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
                    storage.save_data(data, market_name)
                    log_detail(f"股票: {code} | 市场: {market_name} | 交易日期: {date_str} | 状态: 成功 | 来源: {source_used}")
                else:
                    logger.error(f"标的 {code} 获取失败 (所有数据源均不可用)")
                    log_detail(f"股票: {code} | 市场: {market_name} | 交易日期: {date_str} | 状态: 失败")

    # 6. 清理资源
    futu_source.close()
    logger.info("=== 任务运行结束 ===")

if __name__ == "__main__":
    main()
