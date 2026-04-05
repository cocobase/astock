from enum import Enum

class AdjType(Enum):
    QFQ = "qfq"   # 前复权
    HFQ = "hfq"   # 后复权
    NONE = "none" # 不复权

class Market(Enum):
    A_SHARE = "A-Share"
    HK = "HK"
    US = "US"

# 标准化 CSV 字段名
class KlineFields:
    TRADE_DATE = "trade_date"
    STOCK_CODE = "stock_code"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    AMOUNT = "amount"
    ADJ_TYPE = "adj_type"
    SOURCE = "source"
    FETCH_TIME = "fetch_time"

# 标准化字段列表（用于 CSV 表头）
STANDARD_FIELDS = [
    KlineFields.TRADE_DATE,
    KlineFields.STOCK_CODE,
    KlineFields.OPEN,
    KlineFields.HIGH,
    KlineFields.LOW,
    KlineFields.CLOSE,
    KlineFields.VOLUME,
    KlineFields.AMOUNT,
    KlineFields.ADJ_TYPE,
    KlineFields.SOURCE,
    KlineFields.FETCH_TIME
]
