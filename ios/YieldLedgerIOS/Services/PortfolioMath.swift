import Foundation

enum PortfolioMath {
    // 与现有 Web 端一致：采用加权平均成本法，卖出冲减剩余成本。
    static func summarize(trades: [Trade], latestPrice: Double?) -> HoldingSnapshot {
        let orderedTrades = trades.sorted { lhs, rhs in
            if lhs.tradeDate == rhs.tradeDate {
                return lhs.createdAt < rhs.createdAt
            }
            return lhs.tradeDate < rhs.tradeDate
        }

        var totalShares = 0
        var totalCost = 0.0

        for trade in orderedTrades {
            let shares = max(0, trade.shares)
            let price = max(0, trade.price)
            switch trade.type {
            case .buy:
                totalShares += shares
                totalCost += Double(shares) * price
            case .sell:
                guard totalShares > 0 else { continue }
                let sellShares = min(shares, totalShares)
                let averageCost = totalShares > 0 ? totalCost / Double(totalShares) : 0
                totalCost -= averageCost * Double(sellShares)
                totalShares -= sellShares
                if totalShares == 0 {
                    totalCost = 0
                }
            }
        }

        let safeLatestPrice = max(0, latestPrice ?? 0)
        let marketValue = safeLatestPrice * Double(totalShares)
        let profitLoss = marketValue - totalCost
        let averageCost = totalShares > 0 ? totalCost / Double(totalShares) : 0

        return HoldingSnapshot(
            shareCount: totalShares,
            averageCost: averageCost,
            totalCost: totalCost,
            marketValue: marketValue,
            profitLoss: profitLoss
        )
    }
}

