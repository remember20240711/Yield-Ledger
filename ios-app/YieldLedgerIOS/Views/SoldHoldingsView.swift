import SwiftUI

struct SoldHoldingsView: View {
    @ObservedObject var viewModel: PortfolioViewModel
    let holdings: [Holding]

    @State private var detailHolding: Holding?
    @State private var deleteCandidate: Holding?

    var body: some View {
        NavigationStack {
            if holdings.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "tray")
                        .font(.system(size: 48))
                        .foregroundStyle(.quaternary)
                    Text("暂无已卖出的持仓")
                        .font(.title3.weight(.medium))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(.systemGroupedBackground))
                .navigationTitle("已卖出")
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(holdings) { holding in
                            soldCard(holding)
                        }
                    }
                    .padding(16)
                }
                .background(Color(.systemGroupedBackground))
                .navigationTitle("已卖出")
                .navigationBarTitleDisplayMode(.large)
            }
        }
        .sheet(isPresented: Binding(get: { detailHolding != nil }, set: { if !$0 { detailHolding = nil } })) {
            if let holding = detailHolding {
                TransactionsSheet(
                    holding: holding,
                    trades: viewModel.sortedTrades(for: holding),
                    snapshot: viewModel.snapshot(for: holding)
                )
            }
        }
    .confirmationDialog("确认删除该持仓及所有交易记录？", isPresented: Binding(get: { deleteCandidate != nil }, set: { if !$0 { deleteCandidate = nil } }), titleVisibility: .visible) {
            Button("删除", role: .destructive) {
                if let c = deleteCandidate { viewModel.deleteHolding(c) }
                deleteCandidate = nil
            }
            Button("取消", role: .cancel) { deleteCandidate = nil }
        }
    }

    // 加权平均成本法计算已实现盈亏
    private static func computeRealizedPL(trades: [Trade]) -> Double {
        var totalShares = 0.0
        var totalCost = 0.0
        var realizedPL = 0.0
        for trade in trades {
            let shares = max(0, trade.shares)
            let price = max(0, trade.price)
            switch trade.type {
            case .buy:
                totalShares += shares
                totalCost += shares * price
            case .sell:
                guard totalShares > 0 else { continue }
                let sellShares = min(shares, totalShares)
                let avgCost = totalCost / totalShares
                realizedPL += sellShares * (price - avgCost)
                totalCost -= avgCost * sellShares
                totalShares -= sellShares
            }
        }
        return realizedPL
    }

    private func soldCard(_ holding: Holding) -> some View {
        let trades = viewModel.sortedTrades(for: holding)
        let realizedPL = Self.computeRealizedPL(trades: trades)
        let lastTradeDate = trades.last?.tradeDate

        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Text(holding.symbol).font(.headline.weight(.bold))
                        Text(holding.market.rawValue)
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 2)
                            .background(.gray, in: Capsule())
                    }
                    Text(holding.name).font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 3) {
                    Text(realizedPL >= 0 ? "+\(AppFormatters.money(realizedPL, currencyCode: holding.currency))" : AppFormatters.money(realizedPL, currencyCode: holding.currency))
                        .font(.subheadline.weight(.semibold).monospacedDigit())
                        .foregroundStyle(realizedPL >= 0 ? .green : .red)
                    Text("已实现盈亏")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            HStack {
                Label("\(trades.count) 笔交易", systemImage: "arrow.left.arrow.right")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                if let date = lastTradeDate {
                    Text("最后交易 \(date.formatted(date: .abbreviated, time: .omitted))")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }

            Divider()

            HStack(spacing: 16) {
                Button { detailHolding = holding } label: {
                    Label("交易记录", systemImage: "list.bullet.rectangle")
                        .font(.subheadline)
                }
                Spacer()
                Button(role: .destructive) { deleteCandidate = holding } label: {
                    Label("删除", systemImage: "trash")
                        .font(.subheadline)
                }
            }
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.06), radius: 8, x: 0, y: 2)
    }
}
