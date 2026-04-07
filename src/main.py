import argparse
import asyncio
from loguru import logger
from src.core.config_loader import ConfigLoader
from src.core.logger import setup_logger
from src.trading_calendar.checker import CalendarChecker
from src.workflows import SyncDailyWorkflow, InitHistoryWorkflow, CalcMetricsWorkflow


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
            f"  交易所: {status.exchange_code}",
            f"  时区: {status.timezone}",
            f"  当前时间: {status.market_now}",
            f"  当前市场日期: {status.market_date}",
            f"  今日是否交易日: {status.is_trading_day_today}",
            f"  当日交易时段是否结束: {status.is_current_session_closed}",
            f"  最后一个交易日: {status.last_trading_day}",
            f"  日历来源: {status.calendar_source}",
            ""
        ])
    return "\n".join(lines).rstrip()


async def main_async():
    # 1. 初始化配置与日志
    config_loader = ConfigLoader()
    global_settings = config_loader.get_global_settings()
    setup_logger(
        log_root=global_settings.get("log_root", "./logs"),
        rotation=global_settings.get("log_rotation", "00:00")
    )
    
    args = parse_args()
    logger.info("=== 多市场收盘日K获取系统启动 (Phase 2 异步重构) ===")
    
    # 2. 打印市场状态总览 (由于是启动检查，这里可以用 to_thread 封装同步库调用)
    calendar_checker = CalendarChecker()
    market_configs = config_loader.config.get("market_configs", {})
    market_status_overview = await asyncio.to_thread(calendar_checker.get_all_market_statuses, market_configs)
    logger.info("\n" + format_market_status_overview(market_status_overview))

    if args.status:
        logger.info("检测到 --status，仅输出市场状态。")
        logger.info("=== 任务运行结束 ===")
        return

    # 3. 选择并执行工作流
    workflow = None
    if args.run:
        workflow = SyncDailyWorkflow(config_loader)
    elif args.init:
        workflow = InitHistoryWorkflow(config_loader)
    elif args.calc_pct:
        workflow = CalcMetricsWorkflow(config_loader)

    if workflow:
        try:
            await workflow.setup()
            await workflow.run(args)
        except Exception as e:
            logger.exception(f"异步工作流执行过程中发生异常: {e}")
        finally:
            await workflow.cleanup()

    logger.info("=== 任务运行结束 ===")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.warning("用户强制中断程序执行")
