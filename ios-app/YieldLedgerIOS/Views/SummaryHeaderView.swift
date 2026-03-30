import SwiftUI

struct SummaryHeaderView: View {
    let summary: PortfolioSummarySnapshot

    var body: some View {
        VStack(spacing: 0) {
            // Hero 区域：总市值大字
            VStack(spacing: 6) {
                Text("持仓总市值")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(.white.opacity(0.7))
                Text(AppFormatters.money(summary.totalMarketValueBase, currencyCode: summary.baseCurrency))
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundStyle(.white)
                    .contentTransition(.numericText())
            }
            .frame(maxWidth: .infinity)
            .padding(.top, 24)
            .padding(.bottom, 20)

            // 指标行
            HStack(spacing: 0) {
                metric(
                    icon: "yensign.circle.fill",
                    label: "年预计分红",
                    value: AppFormatters.money(summary.totalAnnualDividendBase, currencyCode: summary.baseCurrency)
                )
                divider
                metric(
                    icon: "percent",
                    label: "组合股息率",
                    value: AppFormatters.percent(summary.overallDividendYield)
                )
                divider
                metric(
                    icon: "chart.bar.fill",
                    label: "持仓数量",
                    value: "\(summary.holdingCount) 只"
                )
            }
            .padding(.vertical, 14)
            .background(.white.opacity(0.12))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .padding(.horizontal, 16)
            .padding(.bottom, 20)
        }
        .background(
            LinearGradient(
                colors: [Color(red: 0.09, green: 0.11, blue: 0.21),
                         Color(red: 0.12, green: 0.20, blue: 0.36)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }

    private func metric(icon: String, label: String, value: String) -> some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundStyle(.white.opacity(0.6))
            Text(value)
                .font(.subheadline.weight(.semibold).monospacedDigit())
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.55))
        }
        .frame(maxWidth: .infinity)
    }

    private var divider: some View {
        Rectangle()
            .fill(.white.opacity(0.15))
            .frame(width: 1, height: 36)
    }
}
