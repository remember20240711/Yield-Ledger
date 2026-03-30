import SwiftUI

struct HoldingRowView: View {
    let holding: Holding
    let snapshot: HoldingDisplaySnapshot
    let currentDividendYield: Double?
    let fiveYearAvgYield: Double?
    let annualDividendBase: Double
    let baseCurrency: String
    var portfolioWeight: Double = 0
    let onTapDividend: () -> Void
    let onBuy: () -> Void
    let onSell: () -> Void
    let onShowDetails: () -> Void
    let onDelete: () -> Void

    private var profitColor: Color { snapshot.profitLossBase >= 0 ? Color(red: 0.2, green: 0.78, blue: 0.35) : Color(red: 0.95, green: 0.26, blue: 0.21) }
    private var profitSign: String { snapshot.profitLossBase >= 0 ? "+" : "" }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // 顶栏：标识 + 当前价
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Text(holding.symbol)
                            .font(.headline.weight(.bold))
                        marketBadge
                    }
                    Text(holding.name)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 3) {
                    Text("当前股价")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(priceText)
                        .font(.title3.weight(.bold).monospacedDigit())
                    Text("\(profitSign)\(AppFormatters.money(snapshot.profitLossBase, currencyCode: baseCurrency))")
                        .font(.caption.weight(.medium).monospacedDigit())
                        .foregroundStyle(profitColor)
                }
            }
            .padding(.bottom, 14)

            // 核心指标网格
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                metricCell(label: "股息率", icon: "leaf.fill", tint: .teal) {
                    Button(action: onTapDividend) {
                        HStack(spacing: 4) {
                            Text(currentDividendYield.map { AppFormatters.percent($0) } ?? "—")
                                .font(.subheadline.weight(.semibold).monospacedDigit())
                                .foregroundStyle(.teal)
                            if let avg5 = fiveYearAvgYield {
                                Text("5Y \(AppFormatters.percent(avg5))")
                                    .font(.system(size: 10).weight(.medium))
                                    .foregroundStyle(.secondary)
                                    .padding(.horizontal, 4)
                                    .padding(.vertical, 1)
                                    .background(Color(.tertiarySystemFill), in: Capsule())
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
                metricCell(label: "年预计分红", icon: "banknote.fill", tint: .orange) {
                    Text(AppFormatters.money(annualDividendBase, currencyCode: baseCurrency))
                        .font(.subheadline.weight(.medium).monospacedDigit())
                }
                metricCell(label: "持仓数量", icon: "number", tint: .indigo) {
                    Text(AppFormatters.shares(snapshot.shareCount))
                        .font(.subheadline.weight(.medium).monospacedDigit())
                }
                metricCell(label: "持仓市值", icon: "chart.pie.fill", tint: .blue) {
                    HStack(spacing: 4) {
                        Text(AppFormatters.money(snapshot.marketValueBase, currencyCode: baseCurrency))
                            .font(.subheadline.weight(.medium).monospacedDigit())
                        if portfolioWeight > 0.001 {
                            Text(AppFormatters.percent(portfolioWeight))
                                .font(.system(size: 10).weight(.medium))
                                .foregroundStyle(.blue)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.blue.opacity(0.1), in: Capsule())
                        }
                    }
                }
            }
            .padding(.bottom, 14)

            // 成本行
            HStack {
                Label {
                    Text("成本 \(AppFormatters.money(snapshot.averageCost, currencyCode: holding.currency))")
                } icon: {
                    Image(systemName: "arrow.down.right.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                Spacer()
                if let price = snapshot.currentPrice {
                    Text("现价 \(AppFormatters.money(price, currencyCode: holding.currency))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.bottom, 12)

            Divider()
                .padding(.bottom, 10)

            // 操作栏
            HStack(spacing: 10) {
                actionButton(title: "买入", icon: "plus.circle.fill", style: .primary, action: onBuy)
                actionButton(title: "卖出", icon: "minus.circle.fill", style: .secondary, action: onSell)
                Spacer()
                Button(action: onShowDetails) {
                    Image(systemName: "list.bullet.rectangle")
                        .font(.body)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                Button(action: onDelete) {
                    Image(systemName: "trash")
                        .font(.body)
                        .foregroundStyle(.red.opacity(0.6))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(16)
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.06), radius: 8, x: 0, y: 2)
    }

    // MARK: - Sub‑views

    private var marketBadge: some View {
        Text(holding.market.rawValue)
            .font(.system(size: 10, weight: .bold))
            .foregroundStyle(.white)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(marketColor, in: Capsule())
    }

    private var marketColor: Color {
        switch holding.market {
        case .cn: return Color(red: 0.85, green: 0.2, blue: 0.15)
        case .hk: return Color(red: 0.16, green: 0.5, blue: 0.73)
        case .us: return Color(red: 0.2, green: 0.45, blue: 0.85)
        }
    }

    private var priceText: String {
        guard let price = holding.latestPrice else { return "—" }
        return AppFormatters.money(price, currencyCode: holding.currency)
    }

    private func metricCell<Content: View>(label: String, icon: String, tint: Color, @ViewBuilder content: () -> Content) -> some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundStyle(tint.opacity(0.7))
                .frame(width: 20)
            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                content()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private enum ActionStyle { case primary, secondary }

    private func actionButton(title: String, icon: String, style: ActionStyle, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: icon)
                .font(.subheadline.weight(.semibold))
                .padding(.horizontal, 14)
                .padding(.vertical, 7)
                .foregroundStyle(style == .primary ? .white : .primary)
                .background(
                    style == .primary
                        ? AnyShapeStyle(Color.blue)
                        : AnyShapeStyle(Color(.tertiarySystemFill)),
                    in: Capsule()
                )
        }
        .buttonStyle(.plain)
    }
}
