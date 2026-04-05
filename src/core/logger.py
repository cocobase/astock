import sys
import os
from loguru import logger

def setup_logger(log_root="./logs", rotation="midnight"):
    """
    配置双日志系统：
    1. run.log: 记录系统级运行状态、错误、警告
    2. download_detail.log: 记录每条标的的数据获取明细
    """
    if not os.path.exists(log_root):
        os.makedirs(log_root)

    # 移除默认的控制台输出
    logger.remove()

    # 控制台输出 (INFO 级别)
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")

    # 系统运行日志 run.log
    run_log_path = os.path.join(log_root, "run.log")
    logger.add(
        run_log_path,
        level="INFO",
        rotation=rotation,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        filter=lambda record: "detail" not in record["extra"] # 过滤掉明细日志
    )

    # 下载明细日志 download_detail.log
    detail_log_path = os.path.join(log_root, "download_detail.log")
    logger.add(
        detail_log_path,
        level="INFO",
        rotation=rotation,
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        filter=lambda record: "detail" in record["extra"] # 只记录带 detail 标记的日志
    )

    return logger

# 创建用于明细记录的便捷方法
def log_detail(msg):
    logger.bind(detail=True).info(msg)
