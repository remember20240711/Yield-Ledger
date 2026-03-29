import SwiftUI

struct HoldingRowView: View {
    let holding: Holding
    let snapshot: HoldingSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(holding.symbol)
                    .font(.headline)
                Text(holding.name)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 12) {
                metric("持仓", "\(snapshot.shareCount)")
                metric("现价", priceText)
                metric("成本价", AppFormatters.number(snapshot.averageCost))
            }

            HStack(spacing: 12) {
                metric("市值", AppFormatters.money(snapshot.marketValue, currencyCode: holding.currency))
                Text("盈亏 \(AppFormatters.money(snapshot.profitLoss, currencyCode: holding.currency))")
                    .foregroundStyle(snapshot.profitLoss >= 0 ? .green : .red)
                    .font(.subheadline)
            }
        }
        .padding(.vertical, 4)
    }

    private var priceText: String {
        guard let price = holding.latestPrice else { return "—" }
        return AppFormatters.number(price)
    }

    private func metric(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline)
        }
    }
}

