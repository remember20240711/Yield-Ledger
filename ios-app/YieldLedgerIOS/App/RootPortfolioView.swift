import SwiftUI
import SwiftData

struct RootPortfolioView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.scenePhase) private var scenePhase
    @Query(sort: \Holding.createdAt, order: .forward) private var holdings: [Holding]

    @State private var viewModel: PortfolioViewModel?

    var body: some View {
        Group {
            if let viewModel {
                MainTabView(viewModel: viewModel, holdings: holdings)
            } else {
                ProgressView("正在初始化...")
            }
        }
        .task {
            if viewModel == nil {
                viewModel = PortfolioViewModel(modelContext: modelContext)
            }
            await viewModel?.refreshQuotesOnActive(holdings: holdings)
        }
        .onChange(of: scenePhase) { _, newPhase in
            guard newPhase == .active else { return }
            Task {
                await viewModel?.refreshQuotesOnActive(holdings: holdings)
            }
        }
    }
}

struct MainTabView: View {
    @ObservedObject var viewModel: PortfolioViewModel
    let holdings: [Holding]

    var activeHoldings: [Holding] {
        holdings.filter { PortfolioMath.summarize(trades: $0.trades, latestPrice: $0.latestPrice).shareCount > 0 }
    }

    var soldHoldings: [Holding] {
        holdings.filter { PortfolioMath.summarize(trades: $0.trades, latestPrice: $0.latestPrice).shareCount <= 0 && !$0.trades.isEmpty }
    }

    var body: some View {
        TabView {
            ContentView(viewModel: viewModel, holdings: activeHoldings, allHoldings: holdings)
                .tabItem {
                    Label("当前持仓", systemImage: "chart.pie.fill")
                }
            SoldHoldingsView(viewModel: viewModel, holdings: soldHoldings)
                .tabItem {
                    Label("已卖出", systemImage: "clock.arrow.circlepath")
                }
        }
    }
}
