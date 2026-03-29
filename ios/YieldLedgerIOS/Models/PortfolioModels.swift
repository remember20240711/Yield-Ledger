import Foundation
import SwiftData

// 市场枚举仅用于 UI 与符号转换，不依赖服务端。
enum MarketType: String, CaseIterable, Identifiable, Codable {
    case cn = "CN"
    case hk = "HK"
    case us = "US"

    var id: String { rawValue }

    var defaultCurrency: String {
        switch self {
        case .cn:
            return "CNY"
        case .hk:
            return "HKD"
        case .us:
            return "USD"
        }
    }
}

// 交易类型统一为买入/卖出，后续统计逻辑按此计算。
enum TradeType: String, CaseIterable, Identifiable, Codable {
    case buy = "buy"
    case sell = "sell"

    var id: String { rawValue }
}

// 持仓实体：本地持久化用户标的与最近一次价格缓存。
@Model
final class Holding {
    @Attribute(.unique) var uniqueKey: String
    var symbol: String
    var name: String
    var marketRaw: String
    var currency: String
    var latestPrice: Double?
    var lastPriceUpdatedAt: Date?
    var createdAt: Date

    @Relationship(deleteRule: .cascade, inverse: \Trade.holding)
    var trades: [Trade] = []

    init(symbol: String, name: String, market: MarketType, currency: String) {
        self.symbol = symbol.uppercased()
        self.name = name
        self.marketRaw = market.rawValue
        self.currency = currency
        self.uniqueKey = "\(market.rawValue):\(symbol.uppercased())"
        self.latestPrice = nil
        self.lastPriceUpdatedAt = nil
        self.createdAt = Date()
    }

    var market: MarketType {
        get { MarketType(rawValue: marketRaw) ?? .us }
        set { marketRaw = newValue.rawValue }
    }
}

// 交易实体：仅保存用户输入交易，不保存任何外部财务缓存。
@Model
final class Trade {
    var id: UUID
    var typeRaw: String
    var tradeDate: Date
    var shares: Int
    var price: Double
    var createdAt: Date

    var holding: Holding?

    init(type: TradeType, tradeDate: Date, shares: Int, price: Double, holding: Holding) {
        self.id = UUID()
        self.typeRaw = type.rawValue
        self.tradeDate = tradeDate
        self.shares = shares
        self.price = price
        self.createdAt = Date()
        self.holding = holding
    }

    var type: TradeType {
        get { TradeType(rawValue: typeRaw) ?? .buy }
        set { typeRaw = newValue.rawValue }
    }
}

// 持仓快照：把交易记录计算成可直接渲染的统计值。
struct HoldingSnapshot {
    let shareCount: Int
    let averageCost: Double
    let totalCost: Double
    let marketValue: Double
    let profitLoss: Double
}

