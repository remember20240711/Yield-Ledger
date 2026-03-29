import SwiftUI

struct TradePayload {
    let type: TradeType
    let shares: Int
    let price: Double
    let tradeDate: Date
}

struct TradeSheet: View {
    let holding: Holding
    let tradeType: TradeType
    let onSubmit: (TradePayload) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var shares = 100
    @State private var priceText = ""
    @State private var tradeDate = Date()

    var body: some View {
        NavigationStack {
            Form {
                Section("标的") {
                    Text("\(holding.symbol) · \(holding.name)")
                }
                Section("交易") {
                    Stepper("股数：\(shares)", value: $shares, in: 1 ... 1_000_000, step: 100)
                    TextField("价格", text: $priceText)
                        .keyboardType(.decimalPad)
                    DatePicker("日期", selection: $tradeDate, displayedComponents: .date)
                }
            }
            .navigationTitle(tradeType == .buy ? "买入" : "卖出")
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
                    Button("保存") {
                        let payload = TradePayload(
                            type: tradeType,
                            shares: shares,
                            price: Double(priceText) ?? 0,
                            tradeDate: tradeDate
                        )
                        onSubmit(payload)
                        dismiss()
                    }
                    .disabled((Double(priceText) ?? 0) <= 0)
                }
            }
        }
    }
}

