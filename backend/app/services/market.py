from dataclasses import dataclass
import re


@dataclass
class ResolvedSymbol:
    # 用户输入会被统一映射成数据库代码、Yahoo 代码和市场信息。
    original_symbol: str
    normalized_symbol: str
    yahoo_symbol: str
    market: str
    currency: str


class MarketResolver:
    def resolve(self, symbol: str) -> ResolvedSymbol:
        # 这里兼容 A 股 / 港股 / 美股的常见输入口径。
        raw = symbol.strip().upper().replace(" ", "")
        if not raw:
            raise ValueError("股票代码不能为空")

        if raw.endswith(".HK"):
            digits = raw.split(".")[0].lstrip("0") or "0"
            normalized_code = digits.zfill(5)
            yahoo_code = digits.zfill(4) if len(digits) <= 4 else digits
            return ResolvedSymbol(symbol, f"{normalized_code}.HK", f"{yahoo_code}.HK", "HK", "HKD")

        if raw.endswith(".SS") or raw.endswith(".SZ") or raw.endswith(".BJ"):
            suffix = raw.split(".")[-1]
            code = raw.split(".")[0]
            return ResolvedSymbol(symbol, f"{code}.{suffix}", f"{code}.{suffix}", "CN", "CNY")

        if raw.endswith(".SH"):
            code = raw.split(".")[0]
            return ResolvedSymbol(symbol, f"{code}.SH", f"{code}.SS", "CN", "CNY")

        if raw.isdigit():
            if len(raw) == 6:
                if raw.startswith(("6", "5", "9")):
                    return ResolvedSymbol(symbol, f"{raw}.SH", f"{raw}.SS", "CN", "CNY")
                if raw.startswith(("0", "1", "2", "3")):
                    return ResolvedSymbol(symbol, f"{raw}.SZ", f"{raw}.SZ", "CN", "CNY")
                if raw.startswith(("4", "8")):
                    return ResolvedSymbol(symbol, f"{raw}.BJ", f"{raw}.BJ", "CN", "CNY")
            if len(raw) <= 5:
                digits = raw.lstrip("0") or "0"
                normalized_code = digits.zfill(5)
                yahoo_code = digits.zfill(4) if len(digits) <= 4 else digits
                return ResolvedSymbol(symbol, f"{normalized_code}.HK", f"{yahoo_code}.HK", "HK", "HKD")

        # 美股类别股兼容：BRK.B / BRK-B / BRK_B 统一到数据库 BRK_B，行情代码用 BRK-B。
        class_share = re.match(r"^([A-Z]+)[._-]([A-Z])$", raw)
        if class_share:
            base, klass = class_share.groups()
            return ResolvedSymbol(symbol, f"{base}_{klass}", f"{base}-{klass}", "US", "USD")

        # 其余美股代码保持原样；若存在下划线则转成 Yahoo 兼容的中划线。
        yahoo_symbol = raw.replace("_", "-")
        return ResolvedSymbol(symbol, raw, yahoo_symbol, "US", "USD")
