import Foundation
import SwiftData

enum PortfolioError: LocalizedError {
    case invalidInput(String)
    case notEnoughShares
    case holdingNotFound

    var errorDescription: String? {
        switch self {
        case let .invalidInput(message):
            return message
        case .notEnoughShares:
            return "卖出股数不能超过当前持仓数量"
        case .holdingNotFound:
            return "持仓不存在"
        }
    }
}

@MainActor
final class PortfolioService {
    private let context: ModelContext
    private let quoteService: QuoteProviding

    init(context: ModelContext, quoteService: QuoteProviding = YahooQuoteService()) {
        self.context = context
        self.quoteService = quoteService
    }

    // App 启动或回前台只刷新当前持仓股价，不刷新其他业务数据。
    func refreshAllHoldingQuotes(holdings: [Holding]) async {
        for holding in holdings {
            let snapshot = PortfolioMath.summarize(trades: holding.trades, latestPrice: holding.latestPrice)
            guard snapshot.shareCount > 0 else { continue }
            await refreshQuote(for: holding)
        }
    }

    // 添加新持仓后只刷新对应标的股价。
    func refreshQuote(for holding: Holding) async {
        do {
            let latest = try await quoteService.fetchLatestPrice(symbol: holding.symbol, market: holding.market)
            holding.latestPrice = latest
            holding.lastPriceUpdatedAt = Date()
            try context.save()
        } catch {
            // 行情失败不阻断本地操作，保留已有缓存值。
        }
    }

    // 新建持仓 = 新建标的 + 首笔买入，随后立即刷新该标的价格。
    func addHolding(
        symbol: String,
        name: String,
        market: MarketType,
        currency: String,
        shares: Int,
        price: Double,
        tradeDate: Date
    ) async throws {
        guard shares >= 1 else { throw PortfolioError.invalidInput("股数最少为 1") }
        guard price > 0 else { throw PortfolioError.invalidInput("价格必须大于 0") }

        let normalizedSymbol = symbol.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard !normalizedSymbol.isEmpty else { throw PortfolioError.invalidInput("股票代码不能为空") }

        let key = "\(market.rawValue):\(normalizedSymbol)"
        let descriptor = FetchDescriptor<Holding>(predicate: #Predicate { $0.uniqueKey == key })
        let existing = try context.fetch(descriptor).first
        let targetHolding: Holding

        if let existing {
            targetHolding = existing
        } else {
            let finalName = name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? normalizedSymbol : name
            targetHolding = Holding(
                symbol: normalizedSymbol,
                name: finalName,
                market: market,
                currency: currency.isEmpty ? market.defaultCurrency : currency
            )
            context.insert(targetHolding)
        }

        let trade = Trade(type: .buy, tradeDate: tradeDate, shares: shares, price: price, holding: targetHolding)
        context.insert(trade)
        try context.save()

        await refreshQuote(for: targetHolding)
    }

    // 买入卖出只更新本地交易，不触发全量联网。
    func addTrade(holding: Holding, type: TradeType, shares: Int, price: Double, tradeDate: Date) throws {
        guard shares >= 1 else { throw PortfolioError.invalidInput("股数最少为 1") }
        guard price > 0 else { throw PortfolioError.invalidInput("价格必须大于 0") }

        if type == .sell {
            let snapshot = PortfolioMath.summarize(trades: holding.trades, latestPrice: holding.latestPrice)
            if shares > snapshot.shareCount {
                throw PortfolioError.notEnoughShares
            }
        }

        let trade = Trade(type: type, tradeDate: tradeDate, shares: shares, price: price, holding: holding)
        context.insert(trade)
        try context.save()
    }

    func deleteHolding(_ holding: Holding) throws {
        context.delete(holding)
        try context.save()
    }
}

