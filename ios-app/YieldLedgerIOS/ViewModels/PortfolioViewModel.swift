import Foundation
import SwiftData

struct PortfolioSummarySnapshot {
    let totalMarketValueBase: Double
    let totalAnnualDividendBase: Double
    let overallDividendYield: Double
    let holdingCount: Int
    let baseCurrency: String
}

struct HoldingDisplaySnapshot {
    let shareCount: Double
    let averageCost: Double
    let totalCostBase: Double
    let marketValueBase: Double
    let profitLossBase: Double
    let currentPrice: Double?
    let fxRateToBase: Double
}

@MainActor
final class PortfolioViewModel: ObservableObject {
    private let baseCurrency = "CNY"
    private let fallbackFxRatesToCNY: [String: Double] = [
        "CNY": 1,
        "USD": 7.2,
        "HKD": 0.92
    ]

    @Published var isRefreshing = false
    @Published var errorMessage: String?
    @Published private(set) var dividendDetailsByKey: [String: DividendDetailSnapshot] = [:]
    @Published private(set) var fxRatesToBase: [String: Double] = ["CNY": 1]

    private let service: PortfolioService

    init(modelContext: ModelContext) {
        self.service = PortfolioService(context: modelContext)
    }

    // 前台刷新入口：用于 App 启动和 scene 回到 active。
    // 1. 刷新所有持仓股价
    // 2. 刷新汇率
    // 3. 批量加载所有持仓的股息数据（本地缓存 < 1 天则跳过网络请求）
    func refreshQuotesOnActive(holdings: [Holding]) async {
        guard !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }
        await service.refreshAllHoldingQuotes(holdings: holdings)
        await refreshFxRates(for: holdings)
        for holding in holdings {
            await loadDividendDetail(for: holding)
        }
    }

    func addHolding(
        symbol: String,
        name: String,
        market: MarketType,
        currency: String,
        shares: Double,
        price: Double,
        tradeDate: Date
    ) async {
        do {
            try await service.addHolding(
                symbol: symbol,
                name: name,
                market: market,
                currency: currency,
                shares: shares,
                price: price,
                tradeDate: tradeDate
            )
            // 新增持仓后确保该币种折算率可用，主列表可立即给出正确汇总。
            await refreshFxRates(forCurrencies: [currency])
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addTrade(holding: Holding, type: TradeType, shares: Double, price: Double, tradeDate: Date) {
        do {
            try service.addTrade(holding: holding, type: type, shares: shares, price: price, tradeDate: tradeDate)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteHolding(_ holding: Holding) {
        do {
            try service.deleteHolding(holding)
            dividendDetailsByKey.removeValue(forKey: holding.uniqueKey)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func snapshot(for holding: Holding) -> HoldingSnapshot {
        PortfolioMath.summarize(trades: holding.trades, latestPrice: holding.latestPrice)
    }

    func displaySnapshot(for holding: Holding) -> HoldingDisplaySnapshot {
        let raw = snapshot(for: holding)
        let rate = fxRateToCNY(for: holding.currency)
        let totalCostBase = raw.totalCost * rate
        let marketValueBase = raw.marketValue * rate
        return HoldingDisplaySnapshot(
            shareCount: raw.shareCount,
            averageCost: raw.averageCost,
            totalCostBase: totalCostBase,
            marketValueBase: marketValueBase,
            profitLossBase: marketValueBase - totalCostBase,
            currentPrice: holding.latestPrice,
            fxRateToBase: rate
        )
    }

    func summary(for holdings: [Holding]) -> PortfolioSummarySnapshot {
        let displaySnapshots = holdings.map { displaySnapshot(for: $0) }
        let totalMarketValueBase = displaySnapshots.reduce(0) { $0 + $1.marketValueBase }
        let totalAnnualDividendBase = holdings.reduce(into: 0.0) { partial, holding in
            let shareCount = snapshot(for: holding).shareCount
            partial += annualDividendBase(for: holding, shareCount: shareCount)
        }
        return PortfolioSummarySnapshot(
            totalMarketValueBase: totalMarketValueBase,
            totalAnnualDividendBase: totalAnnualDividendBase,
            overallDividendYield: totalMarketValueBase > 0 ? totalAnnualDividendBase / totalMarketValueBase : 0,
            holdingCount: holdings.count,
            baseCurrency: baseCurrency
        )
    }

    func currentDividendYield(for holding: Holding) -> Double? {
        dividendDetailsByKey[holding.uniqueKey]?.currentDividendYield
    }

    func fiveYearAvgYield(for holding: Holding) -> Double? {
        guard let detail = dividendDetailsByKey[holding.uniqueKey], detail.fiveYearAvgYield > 0 else { return nil }
        return detail.fiveYearAvgYield
    }

    func tenYearAvgYield(for holding: Holding) -> Double? {
        guard let detail = dividendDetailsByKey[holding.uniqueKey], detail.tenYearAvgYield > 0 else { return nil }
        return detail.tenYearAvgYield
    }

    func annualDividendBase(for holding: Holding, shareCount: Double) -> Double {
        let ttmDividend = dividendDetailsByKey[holding.uniqueKey]?.latestDividendTTM ?? 0
        let localAnnual = ttmDividend * max(0, shareCount)
        return localAnnual * fxRateToCNY(for: holding.currency)
    }

    func dividendDetail(for holding: Holding) -> DividendDetailSnapshot? {
        dividendDetailsByKey[holding.uniqueKey]
    }

    func loadDividendDetail(for holding: Holding, force: Bool = false) async {
        // Step 1：内存无数据时，先从本地缓存加载，保证界面立即有内容可显示。
        if dividendDetailsByKey[holding.uniqueKey] == nil,
           let cached = service.loadCachedDividendDetail(for: holding) {
            dividendDetailsByKey[holding.uniqueKey] = cached
        }

        // Step 2：强制刷新、或缓存超过 1 天、或完全没有缓存时，后台联网更新。
        let cacheAge = holding.dividendCachedAt.map { Date().timeIntervalSince($0) } ?? .infinity
        guard force || cacheAge > 86400 else { return }

        do {
            let fresh = try await service.fetchAndCacheDividendDetail(for: holding)
            dividendDetailsByKey[holding.uniqueKey] = fresh
        } catch {
            // 已有缓存时静默失败，不打扰用户；强制刷新失败才提示。
            if force {
                errorMessage = "股息数据加载失败：\(error.localizedDescription)"
            }
        }
    }

    func sortedTrades(for holding: Holding) -> [Trade] {
        holding.trades.sorted { lhs, rhs in
            if lhs.tradeDate == rhs.tradeDate {
                return lhs.createdAt < rhs.createdAt
            }
            return lhs.tradeDate < rhs.tradeDate
        }
    }

    func clearError() {
        errorMessage = nil
    }

    // MARK: - 导出

    func exportData(holdings: [Holding]) -> Data? {
        try? service.exportData(holdings: holdings)
    }

    // MARK: - 导入

    func importData(_ data: Data, holdings: [Holding]) async {
        do {
            let result = try service.importData(data)
            // 导入后刷新新持仓的行情。
            await service.refreshAllHoldingQuotes(holdings: holdings)
            await refreshFxRates(for: holdings)
            errorMessage = "导入成功：\(result.stocks) 只股票 / \(result.transactions) 条交易"
        } catch {
            errorMessage = "导入失败：\(error.localizedDescription)"
        }
    }

    private func refreshFxRates(for holdings: [Holding]) async {
        let currencies = Set(holdings.map { $0.currency })
        await refreshFxRates(forCurrencies: currencies)
    }

    private func refreshFxRates<S: Sequence>(forCurrencies currencies: S) async where S.Element == String {
        let normalized = Set(currencies.map { $0.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() })
        guard !normalized.isEmpty else { return }
        let rates = await service.fetchFxRatesToCNY(currencies: normalized)
        fxRatesToBase.merge(rates) { _, new in new }
    }

    private func fxRateToCNY(for currency: String) -> Double {
        let key = currency.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if let cached = fxRatesToBase[key], cached > 0 {
            return cached
        }
        return fallbackFxRatesToCNY[key] ?? 1
    }
}
