import SwiftUI

struct CompactHoldingRow: View {
    let holding: Holding
    let snapshot: HoldingDisplaySnapshot
    let currentDividendYield: Double?
    let portfolioWeight: Double
    let baseCurrency: String
    let onTap: () -> Void
    let onTapDividend: () -> Void

    private var profitColor: Color { snapshot.profitLossBase >= 0 ? .green : .red }
    private var profitSign: String { snapshot.profitLossBase >= 0 ? "+" : "" }

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                // 左：名称 + 代码
                VStack(alignment: .leading, spacing: 2) {
                    Text(holding.name)
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(.primary)
                    HStack(spacing: 4) {
                        Text(holding.symbol)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                        if portfolioWeight > 0.001 {
                            Text(AppFormatters.percent(portfolioWeight))
                                .font(.system(size: 9, weight: .medium))
                                .foregroundStyle(.blue)
                                .padding(.horizontal, 3)
                                .padding(.vertical, 1)
                                .background(Color.blue.opacity(0.08), in: Capsule())
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                // 中：股息率
                Button(action: onTapDividend) {
                    Text(currentDividendYield.map { AppFormatters.percent($0) } ?? "—")
                        .font(.caption.weight(.semibold).monospacedDigit())
                        .foregroundStyle(.teal)
                }
                .buttonStyle(.plain)
                .frame(width: 56, alignment: .trailing)

                // 右：股价 + 盈亏
                VStack(alignment: .trailing, spacing: 2) {
                    Text(priceText)
                        .font(.subheadline.weight(.semibold).monospacedDigit())
                        .foregroundStyle(.primary)
                    Text("\(profitSign)\(AppFormatters.money(snapshot.profitLossBase, currencyCode: baseCurrency))")
                        .font(.system(size: 10, weight: .medium).monospacedDigit())
                        .foregroundStyle(profitColor)
                }
                .frame(width: 90, alignment: .trailing)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private var priceText: String {
        guard let price = holding.latestPrice else { return "—" }
        return AppFormatters.money(price, currencyCode: holding.currency)
    }
}
