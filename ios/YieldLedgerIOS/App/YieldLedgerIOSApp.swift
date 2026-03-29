import SwiftUI
import SwiftData

@main
struct YieldLedgerIOSApp: App {
    // 使用 SwiftData 持久化，本地底层即 SQLite。
    var body: some Scene {
        WindowGroup {
            RootPortfolioView()
        }
        .modelContainer(for: [Holding.self, Trade.self])
    }
}

