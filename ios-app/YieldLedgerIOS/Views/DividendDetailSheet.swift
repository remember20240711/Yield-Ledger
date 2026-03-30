import Charts
import SwiftUI

struct DividendDetailSheet: View {
    let holding: Holding
    let detail: DividendDetailSnapshot?
    let isLoading: Bool
    let onRefresh: () async -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    header

                    if isLoading {
                        loadingView
                    } else if let detail {
                        yieldChart(detail: detail)
                        priceChart(detail: detail)
                        yearlyTable(detail: detail)
                    } else {
                        emptyView
                    }
                }
                .padding(16)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("股息与价格")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { Task { await onRefresh() } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") { dismiss() }.fontWeight(.semibold)
                }
            }
        }
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text(holding.name)
                        .font(.title2.bold())
                    HStack(spacing: 6) {
                        Text(holding.symbol)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(holding.market.rawValue)
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(.blue, in: Capsule())
                    }
                }
                Spacer()
            }

            HStack(spacing: 0) {
                yieldPill(
                    label: "当前(TTM)",
                    value: detail.map { AppFormatters.percent($0.currentDividendYield) } ?? "—",
                    tint: .teal
                )
                if let d = detail, d.fiveYearAvgYield > 0 {
                    yieldPill(
                        label: "5年平均",
                        value: AppFormatters.percent(d.fiveYearAvgYield),
                        tint: .blue
                    )
                }
                if let d = detail, d.tenYearAvgYield > 0 {
                    yieldPill(
                        label: "10年平均",
                        value: AppFormatters.percent(d.tenYearAvgYield),
                        tint: .indigo
                    )
                }
            }
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.04), radius: 6, y: 2)
    }

    private func yieldPill(label: String, value: String, tint: Color) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title3.weight(.bold).monospacedDigit())
                .foregroundStyle(tint)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Charts

    private func yieldChart(detail: DividendDetailSnapshot) -> some View {
        let points = detail.yearlyPoints.map { (year: $0.year, value: $0.dividendYield * 100) }
        let maxY = max(1.0, (points.map(\.value).max() ?? 1.0) * 1.25)

        return cardSection(title: "最近五年股息率", icon: "chart.xyaxis.line") {
            Chart(points, id: \.year) { item in
                AreaMark(
                    x: .value("年份", String(item.year)),
                    y: .value("股息率", item.value)
                )
                .foregroundStyle(
                    LinearGradient(colors: [.teal.opacity(0.3), .teal.opacity(0.02)], startPoint: .top, endPoint: .bottom)
                )
                LineMark(
                    x: .value("年份", String(item.year)),
                    y: .value("股息率", item.value)
                )
                .foregroundStyle(.teal)
                .lineStyle(StrokeStyle(lineWidth: 2.5))
                PointMark(
                    x: .value("年份", String(item.year)),
                    y: .value("股息率", item.value)
                )
                .foregroundStyle(.teal)
                .symbolSize(36)
                .annotation(position: .top, spacing: 6) {
                    Text(String(format: "%.1f%%", item.value))
                        .font(.system(size: 10, weight: .medium).monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            }
            .chartYScale(domain: 0 ... maxY)
            .chartXAxis { AxisMarks { value in AxisValueLabel { Text(value.as(String.self) ?? "") } } }
            .chartYAxis { AxisMarks(position: .leading) { value in AxisValueLabel { if let v = value.as(Double.self) { Text(String(format: "%.1f%%", v)) } } } }
            .frame(height: 220)
        }
    }

    private func priceChart(detail: DividendDetailSnapshot) -> some View {
        cardSection(title: "最近五年季度收盘价", icon: "chart.line.uptrend.xyaxis") {
            Chart(detail.quarterlyPoints) { item in
                AreaMark(
                    x: .value("季度", item.label),
                    y: .value("价格", item.closePrice)
                )
                .foregroundStyle(
                    LinearGradient(colors: [.orange.opacity(0.25), .orange.opacity(0.02)], startPoint: .top, endPoint: .bottom)
                )
                LineMark(
                    x: .value("季度", item.label),
                    y: .value("价格", item.closePrice)
                )
                .foregroundStyle(.orange)
                .lineStyle(StrokeStyle(lineWidth: 2))
                .interpolationMethod(.catmullRom)
            }
            .chartXAxis { AxisMarks(values: .automatic(desiredCount: 5)) }
            .chartYAxis { AxisMarks(position: .leading) }
            .frame(height: 200)
        }
    }

    // MARK: - Table

    private func yearlyTable(detail: DividendDetailSnapshot) -> some View {
        cardSection(title: "年度明细", icon: "tablecells") {
            VStack(spacing: 0) {
                tableHeader
                ForEach(detail.yearlyPoints) { item in
                    Divider()
                    HStack {
                        Text("\(item.year)")
                            .frame(maxWidth: .infinity, alignment: .leading)
                        Text(AppFormatters.money(item.dividendPerShare, currencyCode: holding.currency))
                            .frame(maxWidth: .infinity, alignment: .trailing)
                        Text(AppFormatters.percent(item.dividendYield))
                            .frame(maxWidth: .infinity, alignment: .trailing)
                            .foregroundStyle(.teal)
                        Text(item.closePrice > 0 ? AppFormatters.money(item.closePrice, currencyCode: holding.currency) : "—")
                            .frame(maxWidth: .infinity, alignment: .trailing)
                    }
                    .font(.subheadline.monospacedDigit())
                    .padding(.vertical, 10)
                }
            }
        }
    }

    private var tableHeader: some View {
        HStack {
            Text("年份").frame(maxWidth: .infinity, alignment: .leading)
            Text("每股分红").frame(maxWidth: .infinity, alignment: .trailing)
            Text("股息率").frame(maxWidth: .infinity, alignment: .trailing)
            Text("年末价格").frame(maxWidth: .infinity, alignment: .trailing)
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(.secondary)
        .padding(.bottom, 6)
    }

    // MARK: - Helpers

    private func cardSection<Content: View>(title: String, icon: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon)
                .font(.headline)
            content()
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.04), radius: 6, y: 2)
    }

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
                .controlSize(.large)
            Text("正在加载股息数据...")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }

    private var emptyView: some View {
        VStack(spacing: 10) {
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 40))
                .foregroundStyle(.quaternary)
            Text("暂无股息数据")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
    }
}
