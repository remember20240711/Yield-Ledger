import SwiftUI

struct ContentView: View {
    @ObservedObject var viewModel: PortfolioViewModel
    let holdings: [Holding]

    @State private var showAddSheet = false
    @State private var tradeSheetState: TradeSheetState?
    @State private var deleteCandidate: Holding?

    var body: some View {
        NavigationStack {
            List {
                if holdings.isEmpty {
                    ContentUnavailableView("暂无持仓", systemImage: "tray")
                } else {
                    ForEach(holdings) { holding in
                        let snapshot = viewModel.snapshot(for: holding)
                        HoldingRowView(holding: holding, snapshot: snapshot)
                            .swipeActions(edge: .leading, allowsFullSwipe: false) {
                                Button("买入") {
                                    tradeSheetState = TradeSheetState(holding: holding, tradeType: .buy)
                                }
                                .tint(.blue)

                                Button("卖出") {
                                    tradeSheetState = TradeSheetState(holding: holding, tradeType: .sell)
                                }
                                .tint(.orange)
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button("删除", role: .destructive) {
                                    deleteCandidate = holding
                                }
                            }
                    }
                }
            }
            .navigationTitle("本地持仓")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if viewModel.isRefreshing {
                        ProgressView()
                    } else {
                        Button("刷新股价") {
                            Task {
                                await viewModel.refreshQuotesOnActive(holdings: holdings)
                            }
                        }
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("添加持仓") {
                        showAddSheet = true
                    }
                }
            }
        }
        .sheet(isPresented: $showAddSheet) {
            AddHoldingSheet { payload in
                Task {
                    await viewModel.addHolding(
                        symbol: payload.symbol,
                        name: payload.name,
                        market: payload.market,
                        currency: payload.currency,
                        shares: payload.shares,
                        price: payload.price,
                        tradeDate: payload.tradeDate
                    )
                }
            }
        }
        .sheet(
            isPresented: Binding(
                get: { tradeSheetState != nil },
                set: { if !$0 { tradeSheetState = nil } }
            )
        ) {
            if let state = tradeSheetState {
                TradeSheet(holding: state.holding, tradeType: state.tradeType) { payload in
                    viewModel.addTrade(
                        holding: state.holding,
                        type: payload.type,
                        shares: payload.shares,
                        price: payload.price,
                        tradeDate: payload.tradeDate
                    )
                }
            }
        }
        .confirmationDialog(
            "确认删除该持仓？",
            isPresented: Binding(
                get: { deleteCandidate != nil },
                set: { if !$0 { deleteCandidate = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("删除", role: .destructive) {
                if let candidate = deleteCandidate {
                    viewModel.deleteHolding(candidate)
                }
                deleteCandidate = nil
            }
            Button("取消", role: .cancel) {
                deleteCandidate = nil
            }
        }
        .alert("提示", isPresented: Binding(get: {
            viewModel.errorMessage != nil
        }, set: { shown in
            if !shown { viewModel.clearError() }
        })) {
            Button("知道了", role: .cancel) {
                viewModel.clearError()
            }
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }
}

private struct TradeSheetState {
    let holding: Holding
    let tradeType: TradeType
}

