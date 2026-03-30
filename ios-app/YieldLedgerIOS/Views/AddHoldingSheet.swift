import SwiftUI

struct AddHoldingPayload {
    let symbol: String
    let name: String
    let market: MarketType
    let currency: String
    let shares: Double
    let price: Double
    let tradeDate: Date
}

struct AddHoldingSheet: View {
    let onSubmit: (AddHoldingPayload) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var searchText = ""
    @State private var selectedSymbol = ""
    @State private var selectedName = ""
    @State private var market: MarketType = .cn
    @State private var currency = "CNY"
    @State private var sharesText = "100"
    @State private var priceText = "1.00"
    @State private var tradeDate = Date()

    @State private var searchResults: [CatalogStock] = []
    @FocusState private var priceFocused: Bool
    @State private var priceBeforeFocus = ""

    private var parsedShares: Double { Double(sharesText) ?? 0 }
    private var parsedPrice: Double { Double(priceText) ?? 0 }
    private var effectiveSymbol: String { selectedSymbol.isEmpty ? searchText.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() : selectedSymbol }
    private var effectiveName: String { selectedName.isEmpty ? effectiveSymbol : selectedName }
    private var isValid: Bool { parsedPrice > 0 && parsedShares > 0 && !effectiveSymbol.isEmpty }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.secondary)
                        TextField("代码、名称或拼音首字母，如 zsyh", text: $searchText)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                            .onChange(of: searchText) { _, newValue in
                                // 选中候选后会设置 searchText，此时不应清除已选状态
                                let expected = selectedName.isEmpty ? "" : "\(selectedName) (\(selectedSymbol))"
                                guard newValue != expected else { return }
                                selectedSymbol = ""
                                selectedName = ""
                                performSearch()
                            }
                        if !searchText.isEmpty {
                            Button { searchText = ""; searchResults = []; selectedSymbol = ""; selectedName = "" } label: {
                                Image(systemName: "xmark.circle.fill").foregroundStyle(.secondary)
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    if !selectedSymbol.isEmpty {
                        HStack(spacing: 8) {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                            Text(selectedName).font(.subheadline)
                            Text(selectedSymbol).font(.caption).foregroundStyle(.secondary)
                            Spacer()
                        }
                        .padding(.vertical, 2)
                    }

                    if !searchResults.isEmpty && selectedSymbol.isEmpty {
                        ForEach(searchResults, id: \.normalizedSymbol) { stock in
                            Button { selectStock(stock) } label: {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(stock.name)
                                            .font(.subheadline)
                                            .foregroundStyle(.primary)
                                        Text(stock.normalizedSymbol)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Text(stock.market)
                                        .font(.caption2)
                                        .foregroundStyle(.tertiary)
                                }
                            }
                        }
                    }

                    Picker("市场", selection: $market) {
                        ForEach(MarketType.allCases) { item in
                            Text(marketLabel(item)).tag(item)
                        }
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: market) { _, newValue in
                        currency = newValue.defaultCurrency
                        performSearch()
                    }
                } header: {
                    Label("股票名称", systemImage: "building.columns")
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
                        Text(currency)
                            .foregroundStyle(.secondary)
                            .font(.subheadline)
                    }
                    DatePicker("交易日期", selection: $tradeDate, displayedComponents: .date)
                } header: {
                    Label("首次建仓", systemImage: "cart.badge.plus")
                } footer: {
                    if parsedShares > 0, parsedPrice > 0 {
                        Text("总金额 \(AppFormatters.money(parsedShares * parsedPrice, currencyCode: currency))")
                            .font(.footnote.monospacedDigit())
                    }
                }
            }
            .navigationTitle("添加持仓")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("确认") { submit() }
                        .fontWeight(.semibold)
                        .disabled(!isValid)
                }
            }
        }
    }

    // MARK: - Search

    private func performSearch() {
        let q = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard q.count >= 1 else { searchResults = []; return }
        searchResults = StockCatalogService.shared.search(query: q, market: market, limit: 15)
    }

    private func selectStock(_ stock: CatalogStock) {
        selectedSymbol = stock.normalizedSymbol
        selectedName = stock.name
        searchText = "\(stock.name) (\(stock.normalizedSymbol))"
        searchResults = []

        if let m = MarketType(rawValue: stock.market) {
            market = m
            currency = m.defaultCurrency
        }
    }

    // MARK: - Actions

    private func stepButton(step: Int) -> some View {
        Button {
            let current = max(1, Int(parsedShares))
            sharesText = String(max(1, current + step))
        } label: {
            Image(systemName: step > 0 ? "plus" : "minus")
                .font(.caption.weight(.bold))
                .frame(width: 28, height: 28)
                .background(Color(.tertiarySystemFill), in: Circle())
        }
        .buttonStyle(.plain)
    }

    private func submit() {
        onSubmit(AddHoldingPayload(
            symbol: effectiveSymbol,
            name: effectiveName,
            market: market,
            currency: currency,
            shares: parsedShares,
            price: parsedPrice,
            tradeDate: tradeDate
        ))
        dismiss()
    }

    private func marketLabel(_ m: MarketType) -> String {
        switch m { case .cn: return "A股"; case .hk: return "港股"; case .us: return "美股" }
    }
}
