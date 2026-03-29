import Foundation
import SwiftData

@MainActor
final class PortfolioViewModel: ObservableObject {
    @Published var isRefreshing = false
    @Published var errorMessage: String?

    private let service: PortfolioService

    init(modelContext: ModelContext) {
        self.service = PortfolioService(context: modelContext)
    }

    // 前台刷新入口：用于 App 启动和 scene 回到 active。
    func refreshQuotesOnActive(holdings: [Holding]) async {
        guard !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }
        await service.refreshAllHoldingQuotes(holdings: holdings)
    }

    func addHolding(
        symbol: String,
        name: String,
        market: MarketType,
        currency: String,
        shares: Int,
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
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addTrade(holding: Holding, type: TradeType, shares: Int, price: Double, tradeDate: Date) {
        do {
            try service.addTrade(holding: holding, type: type, shares: shares, price: price, tradeDate: tradeDate)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteHolding(_ holding: Holding) {
        do {
            try service.deleteHolding(holding)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func snapshot(for holding: Holding) -> HoldingSnapshot {
        PortfolioMath.summarize(trades: holding.trades, latestPrice: holding.latestPrice)
    }

    func clearError() {
        errorMessage = nil
    }
}

