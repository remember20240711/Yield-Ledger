import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @ObservedObject var viewModel: PortfolioViewModel
    let holdings: [Holding]
    var allHoldings: [Holding] = []

    @State private var showAddSheet = false
    @State private var tradeSheetState: TradeSheetState?
    @State private var detailHolding: Holding?
    @State private var dividendHolding: Holding?
    @State private var deleteCandidate: Holding?

    @State private var sortByMarketValue = true
    @State private var listMode = false
    @State private var exportItem: ExportItem?
    @State private var showImportPicker = false
    @State private var showImportConfirm = false
    @State private var pendingImportData: Data?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    let summary = viewModel.summary(for: holdings)

                    SummaryHeaderView(summary: summary)
                        .padding(.horizontal, 16)

                    if holdings.isEmpty {
                        emptyState
                    } else {
                        // 工具栏：数量 + 排序 + 视图切换
                        HStack {
                            Text("\(holdings.count) 只股票")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Spacer()
                            Menu {
                                Button { sortByMarketValue = true } label: {
                                    Label("按市值排序", systemImage: sortByMarketValue ? "checkmark" : "")
                                }
                                Button { sortByMarketValue = false } label: {
                                    Label("按添加时间", systemImage: sortByMarketValue ? "" : "checkmark")
                                }
                            } label: {
                                Label(sortByMarketValue ? "按市值" : "按时间", systemImage: "arrow.up.arrow.down")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            Button {
                                withAnimation(.easeInOut(duration: 0.2)) { listMode.toggle() }
                            } label: {
                                Image(systemName: listMode ? "square.grid.2x2" : "list.bullet")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.horizontal, 20)

                        let totalMV = summary.totalMarketValueBase
                        let sorted = sortByMarketValue
                            ? holdings.sorted { viewModel.displaySnapshot(for: $0).marketValueBase > viewModel.displaySnapshot(for: $1).marketValueBase }
                            : holdings

                        if listMode {
                            // 列表模式：紧凑行
                            LazyVStack(spacing: 0) {
                                ForEach(sorted) { holding in
                                    let snap = viewModel.displaySnapshot(for: holding)
                                    let weight = totalMV > 0 ? snap.marketValueBase / totalMV : 0
                                    CompactHoldingRow(
                                        holding: holding,
                                        snapshot: snap,
                                        currentDividendYield: viewModel.currentDividendYield(for: holding),
                                        portfolioWeight: weight,
                                        baseCurrency: summary.baseCurrency,
                                        onTap: { detailHolding = holding },
                                        onTapDividend: { dividendHolding = holding }
                                    )
                                    .task(id: holding.uniqueKey) {
                                        await viewModel.loadDividendDetail(for: holding)
                                    }
                                    if holding.id != sorted.last?.id {
                                        Divider().padding(.leading, 16)
                                    }
                                }
                            }
                            .background(.background, in: RoundedRectangle(cornerRadius: 12))
                            .padding(.horizontal, 16)
                        } else {
                            // 卡片模式
                            LazyVStack(spacing: 12) {
                                ForEach(sorted) { holding in
                                    let snap = viewModel.displaySnapshot(for: holding)
                                    let weight = totalMV > 0 ? snap.marketValueBase / totalMV : 0
                                    HoldingRowView(
                                        holding: holding,
                                        snapshot: snap,
                                        currentDividendYield: viewModel.currentDividendYield(for: holding),
                                        fiveYearAvgYield: viewModel.fiveYearAvgYield(for: holding),
                                        annualDividendBase: viewModel.annualDividendBase(for: holding, shareCount: snap.shareCount),
                                        baseCurrency: summary.baseCurrency,
                                        portfolioWeight: weight,
                                        onTapDividend: { dividendHolding = holding },
                                        onBuy: { tradeSheetState = TradeSheetState(holding: holding, tradeType: .buy) },
                                        onSell: { tradeSheetState = TradeSheetState(holding: holding, tradeType: .sell) },
                                        onShowDetails: { detailHolding = holding },
                                        onDelete: { deleteCandidate = holding }
                                    )
                                    .task(id: holding.uniqueKey) {
                                        await viewModel.loadDividendDetail(for: holding)
                                    }
                                }
                            }
                            .padding(.horizontal, 16)
                        }
                    }
                }
                .padding(.bottom, 24)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("息流账本")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if viewModel.isRefreshing {
                        ProgressView()
                            .tint(.secondary)
                    }
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Menu {
                        Button { handleExport() } label: {
                            Label("导出备份", systemImage: "square.and.arrow.up")
                        }
                        Button { showImportPicker = true } label: {
                            Label("导入备份", systemImage: "square.and.arrow.down")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .font(.body)
                    }
                    Button { showAddSheet = true } label: {
                        Image(systemName: "plus")
                            .font(.body.weight(.semibold))
                            .foregroundStyle(.white)
                            .frame(width: 30, height: 30)
                            .background(.blue, in: Circle())
                    }
                }
            }
        }
        // --- Sheets ---
        .sheet(item: $exportItem) { item in
            ShareSheet(items: [item.url]).ignoresSafeArea()
        }
        .fileImporter(isPresented: $showImportPicker, allowedContentTypes: [UTType.json], allowsMultipleSelection: false) { result in
            handleImportFilePicked(result: result)
        }
        .confirmationDialog("导入将合并到现有持仓，同代码的股票会追加交易记录。", isPresented: $showImportConfirm, titleVisibility: .visible) {
            Button("确认导入") {
                if let data = pendingImportData { Task { await viewModel.importData(data, holdings: holdings) } }
                pendingImportData = nil
            }
            Button("取消", role: .cancel) { pendingImportData = nil }
        }
        .sheet(isPresented: $showAddSheet) {
            AddHoldingSheet { payload in
                Task {
                    await viewModel.addHolding(
                        symbol: payload.symbol, name: payload.name, market: payload.market,
                        currency: payload.currency, shares: payload.shares, price: payload.price, tradeDate: payload.tradeDate
                    )
                }
            }
        }
        .sheet(isPresented: Binding(get: { tradeSheetState != nil }, set: { if !$0 { tradeSheetState = nil } })) {
            if let state = tradeSheetState {
                let currentShares = viewModel.snapshot(for: state.holding).shareCount
                TradeSheet(
                    holding: state.holding,
                    tradeType: state.tradeType,
                    maxShares: state.tradeType == .sell ? currentShares : nil
                ) { payload in
                    viewModel.addTrade(holding: state.holding, type: payload.type, shares: payload.shares, price: payload.price, tradeDate: payload.tradeDate)
                }
            }
        }
        .sheet(isPresented: Binding(get: { detailHolding != nil }, set: { if !$0 { detailHolding = nil } })) {
            if let holding = detailHolding {
                TransactionsSheet(holding: holding, trades: viewModel.sortedTrades(for: holding), snapshot: viewModel.snapshot(for: holding))
            }
        }
        .sheet(isPresented: Binding(get: { dividendHolding != nil }, set: { if !$0 { dividendHolding = nil } })) {
            if let holding = dividendHolding {
                DividendDetailSheet(holding: holding, detail: viewModel.dividendDetail(for: holding), isLoading: viewModel.dividendDetail(for: holding) == nil) {
                    await viewModel.loadDividendDetail(for: holding, force: true)
                }
            }
        }
        .confirmationDialog("确认删除该持仓及所有交易记录？", isPresented: Binding(get: { deleteCandidate != nil }, set: { if !$0 { deleteCandidate = nil } }), titleVisibility: .visible) {
            Button("删除", role: .destructive) {
                if let c = deleteCandidate { viewModel.deleteHolding(c) }
                deleteCandidate = nil
            }
            Button("取消", role: .cancel) { deleteCandidate = nil }
        }
        .alert("提示", isPresented: Binding(get: { viewModel.errorMessage != nil }, set: { if !$0 { viewModel.clearError() } })) {
            Button("知道了", role: .cancel) { viewModel.clearError() }
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 48))
                .foregroundStyle(.quaternary)
            Text("暂无持仓")
                .font(.title3.weight(.medium))
                .foregroundStyle(.secondary)
            Text("点击右上角 + 添加你的第一笔持仓")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
            Button {
                showAddSheet = true
            } label: {
                Label("添加持仓", systemImage: "plus")
                    .font(.subheadline.weight(.semibold))
                    .padding(.horizontal, 20)
                    .padding(.vertical, 10)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.regular)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }

    // MARK: - Export / Import

    private func handleExport() {
        guard let data = viewModel.exportData(holdings: allHoldings.isEmpty ? holdings : allHoldings) else { return }
        let fmt = DateFormatter(); fmt.dateFormat = "yyyyMMdd-HHmmss"
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("yield-ledger-backup-\(fmt.string(from: Date())).json")
        do { try data.write(to: url); exportItem = ExportItem(url: url) } catch {}
    }

    private func handleImportFilePicked(result: Result<[URL], Error>) {
        guard case .success(let urls) = result, let url = urls.first else { return }
        guard url.startAccessingSecurityScopedResource() else { return }
        defer { url.stopAccessingSecurityScopedResource() }
        guard let data = try? Data(contentsOf: url) else { return }
        pendingImportData = data
        showImportConfirm = true
    }
}

// MARK: - Helpers

private struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}

private struct ExportItem: Identifiable {
    let id = UUID()
    let url: URL
}

private struct TradeSheetState {
    let holding: Holding
    let tradeType: TradeType
}
