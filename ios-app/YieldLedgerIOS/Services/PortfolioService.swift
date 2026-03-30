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
            print("[Quote] \(holding.symbol) -> \(latest)")
        } catch {
            print("[Quote] \(holding.symbol) FAILED: \(error)")
        }
    }

    // 从本地缓存读取股息详情，无缓存时返回 nil。
    func loadCachedDividendDetail(for holding: Holding) -> DividendDetailSnapshot? {
        guard holding.dividendCachedAt != nil,
              let ttm = holding.dividendTTM,
              let currentYield = holding.dividendCurrentYield
        else { return nil }
        let decoder = JSONDecoder()
        let yearly = holding.dividendYearlyData
            .flatMap { try? decoder.decode([DividendYearPoint].self, from: $0) } ?? []
        let quarterly = holding.dividendQuarterlyData
            .flatMap { try? decoder.decode([QuarterlyPricePoint].self, from: $0) } ?? []
        return DividendDetailSnapshot(
            latestDividendTTM: ttm,
            currentDividendYield: currentYield,
            fiveYearAvgYield: holding.dividendFiveYearAvgYield ?? 0,
            tenYearAvgYield: holding.dividendTenYearAvgYield ?? 0,
            yearlyPoints: yearly,
            quarterlyPoints: quarterly
        )
    }

    // 联网拉取最新股息数据并写入本地缓存。
    func fetchAndCacheDividendDetail(for holding: Holding) async throws -> DividendDetailSnapshot {
        let snapshot = try await quoteService.fetchDividendDetail(symbol: holding.symbol, market: holding.market)
        let encoder = JSONEncoder()
        holding.dividendTTM = snapshot.latestDividendTTM
        holding.dividendCurrentYield = snapshot.currentDividendYield
        holding.dividendFiveYearAvgYield = snapshot.fiveYearAvgYield
        holding.dividendTenYearAvgYield = snapshot.tenYearAvgYield
        holding.dividendYearlyData = try? encoder.encode(snapshot.yearlyPoints)
        holding.dividendQuarterlyData = try? encoder.encode(snapshot.quarterlyPoints)
        holding.dividendCachedAt = Date()
        try? context.save()
        return snapshot
    }

    // 汇总口径按 CNY 展示，汇率在内存中维护，避免多币种直接相加。
    func fetchFxRatesToCNY(currencies: Set<String>) async -> [String: Double] {
        await quoteService.fetchFxRatesToCNY(currencies: currencies)
    }

    // 新建持仓 = 新建标的 + 首笔买入，随后立即刷新该标的价格。
    func addHolding(
        symbol: String,
        name: String,
        market: MarketType,
        currency: String,
        shares: Double,
        price: Double,
        tradeDate: Date
    ) async throws {
        guard shares > 0 else { throw PortfolioError.invalidInput("股数必须大于 0") }
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
    func addTrade(holding: Holding, type: TradeType, shares: Double, price: Double, tradeDate: Date) throws {
        guard shares > 0 else { throw PortfolioError.invalidInput("股数必须大于 0") }
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

    // MARK: - 备份导出

    func exportData(holdings: [Holding]) throws -> Data {
        let dateFormatter = ISO8601DateFormatter()
        let dayFormatter = DateFormatter()
        dayFormatter.dateFormat = "yyyy-MM-dd"

        let stocks: [[String: Any]] = holdings.map { holding in
            let trades = holding.trades.sorted {
                $0.tradeDate == $1.tradeDate ? $0.createdAt < $1.createdAt : $0.tradeDate < $1.tradeDate
            }
            let transactions: [[String: Any]] = trades.map { trade in
                [
                    "transaction_type": trade.type.rawValue,
                    "trade_date": dayFormatter.string(from: trade.tradeDate),
                    "shares": trade.shares,
                    "average_price": trade.price,
                    "total_amount": trade.shares * trade.price,
                ]
            }
            var item: [String: Any] = [
                "symbol": holding.symbol,
                "name": holding.name,
                "market": holding.market.rawValue,
                "currency": holding.currency,
                "transactions": transactions,
                "dividends": [],
            ]
            if let price = holding.latestPrice {
                item["last_price"] = price
            }
            return item
        }

        let payload: [String: Any] = [
            "version": "1.0",
            "exported_at": dateFormatter.string(from: Date()),
            "stocks": stocks,
        ]
        return try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
    }

    // MARK: - 备份导入

    // 支持导入 Web 端和 iOS 端导出的 JSON 备份，同代码持仓直接合并交易。
    func importData(_ data: Data) throws -> (stocks: Int, transactions: Int) {
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let stocksArray = root["stocks"] as? [[String: Any]]
        else {
            throw PortfolioError.invalidInput("备份文件格式无效，缺少 stocks 数组")
        }

        let dayFormatter = DateFormatter()
        dayFormatter.dateFormat = "yyyy-MM-dd"
        let iso8601 = ISO8601DateFormatter()

        var importedStocks = 0
        var importedTransactions = 0

        for item in stocksArray {
            // 优先用 normalized_symbol，兼容 Web 端备份格式。
            let rawSymbol = (item["normalized_symbol"] as? String
                ?? item["symbol"] as? String ?? "")
                .trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
            guard !rawSymbol.isEmpty else { continue }

            let marketRaw = (item["market"] as? String ?? "US").uppercased()
            let market = MarketType(rawValue: marketRaw) ?? .us
            let currency = (item["currency"] as? String ?? market.defaultCurrency)
                .trimmingCharacters(in: .whitespacesAndNewlines)
            let name = (item["name"] as? String ?? rawSymbol)
                .trimmingCharacters(in: .whitespacesAndNewlines)
            let lastPrice = item["last_price"] as? Double

            let key = "\(market.rawValue):\(rawSymbol)"
            let descriptor = FetchDescriptor<Holding>(predicate: #Predicate { $0.uniqueKey == key })
            let existing = try context.fetch(descriptor).first
            let holding: Holding
            if let existing {
                holding = existing
            } else {
                holding = Holding(symbol: rawSymbol, name: name, market: market, currency: currency)
                context.insert(holding)
            }
            if let price = lastPrice {
                holding.latestPrice = price
            }

            // 导入前先收集已有交易的指纹（日期+类型+股数+价格），防止重复导入。
            let existingFingerprints: Set<String> = Set(holding.trades.map { trade in
                let d = dayFormatter.string(from: trade.tradeDate)
                return "\(trade.typeRaw)|\(d)|\(trade.shares)|\(trade.price)"
            })

            let transactions = item["transactions"] as? [[String: Any]] ?? []
            for tx in transactions {
                let typeRaw = tx["transaction_type"] as? String ?? "buy"
                let tradeType = TradeType(rawValue: typeRaw) ?? .buy
                let sharesValue = (tx["shares"] as? NSNumber)?.doubleValue ?? 0
                let price = (tx["average_price"] as? NSNumber)?.doubleValue ?? 0
                guard sharesValue > 0, price > 0 else { continue }

                var tradeDate = Date()
                if let dateStr = tx["trade_date"] as? String {
                    tradeDate = dayFormatter.date(from: dateStr)
                        ?? iso8601.date(from: dateStr)
                        ?? Date()
                }

                let fingerprint = "\(typeRaw)|\(dayFormatter.string(from: tradeDate))|\(sharesValue)|\(price)"
                guard !existingFingerprints.contains(fingerprint) else { continue }

                let trade = Trade(type: tradeType, tradeDate: tradeDate, shares: sharesValue, price: price, holding: holding)
                context.insert(trade)
                importedTransactions += 1
            }
            importedStocks += 1
        }

        try context.save()
        return (importedStocks, importedTransactions)
    }
}
