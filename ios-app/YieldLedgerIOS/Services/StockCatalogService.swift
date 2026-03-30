import Foundation

struct CatalogStock {
    let symbol: String
    let normalizedSymbol: String
    let name: String
    let market: String
    let currency: String
    let pinyin: String // 拼音首字母，如 "zsyh"
}

@MainActor
final class StockCatalogService {
    static let shared = StockCatalogService()

    private var stocks: [CatalogStock] = []
    private var loaded = false

    private init() {}

    func ensureLoaded() {
        guard !loaded else { return }
        loaded = true
        loadCatalog()
    }

    // 搜索：支持代码、名称、拼音首字母
    func search(query: String, market: MarketType? = nil, limit: Int = 20) -> [CatalogStock] {
        ensureLoaded()
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return [] }

        var scored: [(Int, CatalogStock)] = []

        for stock in stocks {
            if let m = market, stock.market != m.rawValue { continue }

            let symLower = stock.symbol.lowercased()
            let nsLower = stock.normalizedSymbol.lowercased()
            let nameLower = stock.name.lowercased()
            let py = stock.pinyin

            let score: Int
            if symLower == q || nsLower == q {
                score = 0 // 精确匹配代码
            } else if symLower.hasPrefix(q) || nsLower.hasPrefix(q) {
                score = 1 // 代码前缀匹配
            } else if py == q {
                score = 2 // 拼音精确
            } else if py.hasPrefix(q) {
                score = 3 // 拼音前缀
            } else if nameLower.hasPrefix(q) {
                score = 4 // 名称前缀
            } else if nameLower.contains(q) {
                score = 5 // 名称包含
            } else if symLower.contains(q) || nsLower.contains(q) {
                score = 6 // 代码包含
            } else if py.contains(q) {
                score = 7 // 拼音包含
            } else {
                continue
            }

            scored.append((score, stock))
            if scored.count > limit * 10 { break } // 性能保护
        }

        scored.sort { $0.0 < $1.0 }
        return Array(scored.prefix(limit).map(\.1))
    }

    private func loadCatalog() {
        guard let url = Bundle.main.url(forResource: "StockCatalog", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let array = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]]
        else { return }

        stocks.reserveCapacity(array.count)
        for item in array {
            guard let symbol = item["s"] as? String,
                  let name = item["n"] as? String,
                  let market = item["m"] as? String,
                  let currency = item["c"] as? String
            else { continue }
            let ns = (item["ns"] as? String) ?? symbol
            let py = (item["p"] as? String) ?? ""
            stocks.append(CatalogStock(
                symbol: symbol,
                normalizedSymbol: ns,
                name: name,
                market: market,
                currency: currency,
                pinyin: py
            ))
        }
    }
}
