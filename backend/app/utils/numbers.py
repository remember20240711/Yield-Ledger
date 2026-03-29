from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union


ZERO = Decimal("0")
Number = Union[Decimal, float, int, str]


def to_decimal(value: Optional[object], default: str = "0") -> Decimal:
    # 所有外部数据先转 Decimal，再做统一量化，避免浮点误差串到数据库。
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize(value: Number, places: str) -> Decimal:
    # 金额、价格、股息率等都复用同一套四舍五入口径。
    return to_decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def money(value: Number) -> Decimal:
    return quantize(value, "0.01")


def price(value: Number) -> Decimal:
    return quantize(value, "0.0001")


def trade_price(value: Number) -> Decimal:
    return quantize(value, "0.01")


def pct(value: Number) -> Decimal:
    return quantize(value, "0.01")


def shares(value: Number) -> Decimal:
    return quantize(value, "0.0000")


def as_float(value: Number) -> float:
    return float(value)
