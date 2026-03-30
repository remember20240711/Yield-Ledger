import SwiftUI

struct TradePayload {
    let type: TradeType
    let shares: Double
    let price: Double
    let tradeDate: Date
}

struct TradeSheet: View {
    let holding: Holding
    let tradeType: TradeType
    let maxShares: Double?
    let onSubmit: (TradePayload) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var sharesText = "100"
    @State private var priceText = ""
    @State private var tradeDate = Date()
    @FocusState private var priceFocused: Bool
    @State private var priceBeforeFocus = ""

    private var parsedShares: Double { Double(sharesText) ?? 0 }
    private var parsedPrice: Double { Double(priceText) ?? 0 }
    private var isBuy: Bool { tradeType == .buy }
    private var isSell: Bool { tradeType == .sell }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack(spacing: 10) {
                        Image(systemName: isBuy ? "arrow.up.circle.fill" : "arrow.down.circle.fill")
                            .font(.title2)
                            .foregroundStyle(isBuy ? .blue : .orange)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(holding.name)
                                .font(.headline)
                            HStack(spacing: 6) {
                                Text(holding.symbol)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                if isSell, let max = maxShares, max > 0 {
                                    Text("可卖 \(AppFormatters.shares(max)) 股")
                                        .font(.caption)
                                        .foregroundStyle(.orange)
                                }
                            }
                        }
                    }
                    .listRowBackground(Color.clear)
                }

                Section {
                    HStack {
                        Text("股数")
                        Spacer()
                        stepButton(step: -100)
                        TextField("100", text: $sharesText)
                            .multilineTextAlignment(.center)
                            .keyboardType(.decimalPad)
                            .frame(width: 80)
                            .padding(.vertical, 6)
                            .background(Color(.tertiarySystemFill), in: RoundedRectangle(cornerRadius: 8))
                        stepButton(step: 100)
                        // 卖出时显示"全部"按钮
                        if isSell, let max = maxShares, max > 0 {
                            Button("全部") {
                                sharesText = max == floor(max) ? String(Int(max)) : String(max)
                            }
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.orange)
                        }
                    }
                    HStack {
                        Text("价格")
                        Spacer()
                        TextField("输入价格", text: $priceText)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.decimalPad)
                            .focused($priceFocused)
                            .onChange(of: priceFocused) { _, focused in
                                if focused {
                                    priceBeforeFocus = priceText
                                    priceText = ""
                                } else if priceText.isEmpty {
                                    priceText = priceBeforeFocus
                                }
                            }
                        Text(holding.currency)
                            .foregroundStyle(.secondary)
                            .font(.subheadline)
                    }
                    DatePicker("交易日期", selection: $tradeDate, displayedComponents: .date)
                } header: {
                    Label("交易信息", systemImage: "arrow.left.arrow.right")
                } footer: {
                    VStack(alignment: .leading, spacing: 4) {
                        if parsedShares > 0, parsedPrice > 0 {
                            Text("总金额 \(AppFormatters.money(parsedShares * parsedPrice, currencyCode: holding.currency))")
                                .font(.footnote.monospacedDigit())
                        }
                        if isSell, let max = maxShares, parsedShares > max {
                            Text("卖出股数不能超过当前持仓 \(AppFormatters.shares(max)) 股")
                                .font(.footnote)
                                .foregroundStyle(.red)
                        }
                    }
                }
            }
            .navigationTitle(isBuy ? "买入" : "卖出")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                if let latest = holding.latestPrice, latest > 0 {
                    priceText = AppFormatters.number(latest)
                } else {
                    priceText = "1.00"
                }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("确认") {
                        onSubmit(TradePayload(type: tradeType, shares: parsedShares, price: parsedPrice, tradeDate: tradeDate))
                        dismiss()
                    }
                    .fontWeight(.semibold)
                    .disabled(parsedPrice <= 0 || parsedShares <= 0 || exceedsMax)
                }
            }
        }
    }

    private var exceedsMax: Bool {
        guard isSell, let max = maxShares else { return false }
        return parsedShares > max
    }

    private func stepButton(step: Int) -> some View {
        Button {
            var next = Double(max(0, Int(parsedShares) + step))
            if next < 0 { next = 0 }
            // 卖出时 + 不超过持仓上限
            if isSell, let max = maxShares, next > max {
                next = max
            }
            sharesText = next == floor(next) ? String(Int(next)) : String(next)
        } label: {
            Image(systemName: step > 0 ? "plus" : "minus")
                .font(.caption.weight(.bold))
                .frame(width: 28, height: 28)
                .background(Color(.tertiarySystemFill), in: Circle())
        }
        .buttonStyle(.plain)
    }
}
