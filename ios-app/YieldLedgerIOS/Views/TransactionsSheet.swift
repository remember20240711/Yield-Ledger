import SwiftUI

struct TransactionsSheet: View {
    let holding: Holding
    let trades: [Trade]
    let snapshot: HoldingSnapshot

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    summaryCards
                    tradesSection
                }
                .padding(16)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("\(holding.symbol) 持仓详情")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") { dismiss() }.fontWeight(.semibold)
                }
            }
        }
    }

    // MARK: - Summary Cards

    private var summaryCards: some View {
        HStack(spacing: 10) {
            summaryPill(label: "持仓", value: "\(AppFormatters.shares(snapshot.shareCount)) 股", icon: "number", tint: .blue)
            summaryPill(label: "均价", value: AppFormatters.money(snapshot.averageCost, currencyCode: holding.currency), icon: "equal.circle.fill", tint: .orange)
            summaryPill(label: "总成本", value: AppFormatters.money(snapshot.totalCost, currencyCode: holding.currency), icon: "banknote.fill", tint: .indigo)
        }
    }

    private func summaryPill(label: String, value: String, icon: String, tint: Color) -> some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundStyle(tint)
            Text(value)
                .font(.subheadline.weight(.semibold).monospacedDigit())
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 14)
        .background(.background, in: RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.04), radius: 4, y: 1)
    }

    // MARK: - Trades

    private var tradesSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            Label("交易记录", systemImage: "clock.arrow.circlepath")
                .font(.headline)
                .padding(.bottom, 12)

            ForEach(Array(trades.enumerated()), id: \.element.id) { index, trade in
                if index > 0 { Divider().padding(.leading, 40) }
                tradeRow(trade)
            }
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.04), radius: 6, y: 2)
    }

    private func tradeRow(_ trade: Trade) -> some View {
        let isBuy = trade.type == .buy

        return HStack(spacing: 12) {
            // 时间线圆点
            Circle()
                .fill(isBuy ? Color.blue : Color.orange)
                .frame(width: 8, height: 8)
                .padding(.leading, 4)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(isBuy ? "买入" : "卖出")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(isBuy ? .blue : .orange)
                    Spacer()
                    Text(trade.tradeDate.formatted(date: .abbreviated, time: .omitted))
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                HStack(spacing: 16) {
                    Label("\(AppFormatters.shares(trade.shares)) 股", systemImage: "number")
                    Label(AppFormatters.money(trade.price, currencyCode: holding.currency), systemImage: "tag")
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                Text("总额 \(AppFormatters.money(trade.shares * trade.price, currencyCode: holding.currency))")
                    .font(.caption.weight(.medium).monospacedDigit())
                    .foregroundStyle(.primary.opacity(0.7))
            }
        }
        .padding(.vertical, 10)
    }
}
