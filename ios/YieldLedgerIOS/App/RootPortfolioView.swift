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
                ContentView(viewModel: viewModel, holdings: holdings)
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

