import SwiftUI

struct AddHoldingPayload {
    let symbol: String
    let name: String
    let market: MarketType
    let currency: String
    let shares: Int
    let price: Double
    let tradeDate: Date
}

struct AddHoldingSheet: View {
    let onSubmit: (AddHoldingPayload) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var symbol = ""
    @State private var name = ""
    @State private var market: MarketType = .cn
    @State private var currency = "CNY"
    @State private var shares = 100
    @State private var priceText = "1.00"
    @State private var tradeDate = Date()

    var body: some View {
        NavigationStack {
            Form {
                Section("标的") {
                    TextField("股票代码，例如 600036.SH / AAPL", text: $symbol)
                        .textInputAutocapitalization(.characters)
                    TextField("股票名称", text: $name)
                    Picker("市场", selection: $market) {
                        ForEach(MarketType.allCases) { item in
                            Text(item.rawValue).tag(item)
                        }
                    }
                    .onChange(of: market) { _, newValue in
                        currency = newValue.defaultCurrency
                    }
                    TextField("币种", text: $currency)
                        .textInputAutocapitalization(.characters)
                }

                Section("首次建仓") {
                    Stepper("股数：\(shares)", value: $shares, in: 1 ... 1_000_000, step: 100)
                    TextField("价格", text: $priceText)
                        .keyboardType(.decimalPad)
                    DatePicker("日期", selection: $tradeDate, displayedComponents: .date)
                }
            }
            .navigationTitle("添加持仓")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存") {
                        let parsedPrice = Double(priceText) ?? 0
                        onSubmit(
                            AddHoldingPayload(
                                symbol: symbol,
                                name: name,
                                market: market,
                                currency: currency,
                                shares: shares,
                                price: parsedPrice,
                                tradeDate: tradeDate
                            )
                        )
                        dismiss()
                    }
                    .disabled((Double(priceText) ?? 0) <= 0 || symbol.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

