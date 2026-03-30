import SwiftUI
import SwiftData

@main
struct YieldLedgerIOSApp: App {
    var body: some Scene {
        WindowGroup {
            RootPortfolioView()
        }
        .modelContainer(for: [Holding.self, Trade.self])
    }
}
