import Foundation

// 股票搜索结果
struct StockSearchResult: Identifiable {
    let symbol: String
    let name: String
    let exchange: String
    var id: String { symbol }
}

@MainActor
protocol QuoteProviding {
    func fetchLatestPrice(symbol: String, market: MarketType) async throws -> Double
    func fetchDividendDetail(symbol: String, market: MarketType) async throws -> DividendDetailSnapshot
    func fetchFxRatesToCNY(currencies: Set<String>) async -> [String: Double]
    func searchStocks(query: String) async -> [StockSearchResult]
}

enum QuoteError: LocalizedError {
    case invalidURL
    case emptyData
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "行情请求地址无效"
        case .emptyData:
            return "行情数据为空"
        case .invalidResponse:
            return "行情数据解析失败"
        }
    }
}

// 股息年度点：用于最近五年图表与明细表。
struct DividendYearPoint: Identifiable, Codable {
    let year: Int
    let dividendPerShare: Double
    let dividendYield: Double
    let closePrice: Double

    var id: Int { year }
}

// 季度价格点：用于"最近五年股息与价格"双轴图。
struct QuarterlyPricePoint: Identifiable, Codable {
    let year: Int
    let quarter: Int
    let label: String
    let closePrice: Double

    var id: String { "\(year)-Q\(quarter)" }
}

// 股息详情快照：仅在内存中使用，不落地持久化。
struct DividendDetailSnapshot {
    let latestDividendTTM: Double
    let currentDividendYield: Double
    let fiveYearAvgYield: Double
    let tenYearAvgYield: Double
    let yearlyPoints: [DividendYearPoint]
    let quarterlyPoints: [QuarterlyPricePoint]
}

// iOS 客户端直接走公开 Yahoo 行情接口，不依赖自建后端。
@MainActor
final class YahooQuoteService: QuoteProviding {

    private func yahooRequest(url: URL) -> URLRequest {
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 15)
        req.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)", forHTTPHeaderField: "User-Agent")
        return req
    }

    private func fetchYahooData(from url: URL) async throws -> Data {
        let (data, response) = try await URLSession.shared.data(for: yahooRequest(url: url))
        guard let http = response as? HTTPURLResponse else {
            print("[Yahoo] no HTTP response for \(url)")
            throw QuoteError.invalidResponse
        }
        guard (200 ... 299).contains(http.statusCode) else {
            print("[Yahoo] HTTP \(http.statusCode) for \(url)")
            throw QuoteError.invalidResponse
        }
        guard !data.isEmpty else {
            print("[Yahoo] empty data for \(url)")
            throw QuoteError.emptyData
        }
        return data
    }

    // MARK: - 股价查询（三路容灾）

    func fetchLatestPrice(symbol: String, market: MarketType) async throws -> Double {
        // 主 API：Yahoo Finance（全球覆盖）
        if let price = try? await fetchPriceFromYahoo(symbol: symbol, market: market), price > 0 {
            print("[Quote] \(symbol) via Yahoo -> \(price)")
            return price
        }
        // 备选 1：腾讯财经（A股/港股）
        if market != .us, let price = try? await fetchPriceFromTencent(symbol: symbol, market: market), price > 0 {
            print("[Quote] \(symbol) via Tencent -> \(price)")
            return price
        }
        // 备选 2：新浪财经（A股/港股）
        if market != .us, let price = try? await fetchPriceFromSina(symbol: symbol, market: market), price > 0 {
            print("[Quote] \(symbol) via Sina -> \(price)")
            return price
        }
        print("[Quote] \(symbol) all 3 sources failed")
        throw QuoteError.emptyData
    }

    // --- Yahoo Finance ---
    private func fetchPriceFromYahoo(symbol: String, market: MarketType) async throws -> Double {
        let yahooSymbol = normalizeForYahoo(symbol: symbol, market: market)
        guard let encoded = yahooSymbol.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed),
              !encoded.isEmpty,
              let url = URL(string: "https://query1.finance.yahoo.com/v8/finance/chart/\(encoded)?range=1d&interval=1d&includePrePost=false&events=div")
        else { throw QuoteError.invalidURL }

        let data = try await fetchYahooData(from: url)
        let decoded = try JSONDecoder().decode(YahooChartResponse.self, from: data)
        guard let first = decoded.chart.result?.first else { throw QuoteError.emptyData }
        return first.meta.regularMarketPrice ?? first.meta.previousClose ?? first.meta.chartPreviousClose ?? 0
    }

    // --- 腾讯财经 ---
    private func fetchPriceFromTencent(symbol: String, market: MarketType) async throws -> Double {
        let tencentSymbol = normalizeForTencent(symbol: symbol, market: market)
        guard let url = URL(string: "https://qt.gtimg.cn/q=\(tencentSymbol)") else { throw QuoteError.invalidURL }

        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10)
        req.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw QuoteError.invalidResponse
        }
        // 响应格式: v_sh601988="1~中国银行~601988~4.15~4.14~..."
        guard let text = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .ascii) else {
            throw QuoteError.emptyData
        }
        let fields = text.components(separatedBy: "~")
        // 字段 3 = 当前价，字段 4 = 昨收
        if fields.count > 3, let price = Double(fields[3]), price > 0 { return price }
        if fields.count > 4, let close = Double(fields[4]), close > 0 { return close }
        throw QuoteError.emptyData
    }

    // --- 新浪财经 ---
    private func fetchPriceFromSina(symbol: String, market: MarketType) async throws -> Double {
        let sinaSymbol = normalizeForSina(symbol: symbol, market: market)
        guard let url = URL(string: "https://hq.sinajs.cn/list=\(sinaSymbol)") else { throw QuoteError.invalidURL }

        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10)
        req.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        req.setValue("https://finance.sina.com.cn", forHTTPHeaderField: "Referer")
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw QuoteError.invalidResponse
        }
        // 响应格式: var hq_str_sh601988="中国银行,4.150,4.140,4.150,..."
        let gbkEncoding = CFStringConvertEncodingToNSStringEncoding(CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue))
        guard let text = String(data: data, encoding: .utf8) ?? String(data: data, encoding: String.Encoding(rawValue: gbkEncoding)) else {
            throw QuoteError.emptyData
        }
        guard let start = text.firstIndex(of: "\""), let end = text.lastIndex(of: "\""), start < end else {
            throw QuoteError.emptyData
        }
        let content = text[text.index(after: start) ..< end]
        let fields = content.components(separatedBy: ",")
        if market == .hk {
            // 港股新浪格式：字段 6 = 当前价，字段 3 = 昨收
            if fields.count > 6, let price = Double(fields[6]), price > 0 { return price }
            if fields.count > 3, let close = Double(fields[3]), close > 0 { return close }
        } else {
            // A股新浪格式：字段 3 = 当前价，字段 2 = 昨收
            if fields.count > 3, let price = Double(fields[3]), price > 0 { return price }
            if fields.count > 2, let close = Double(fields[2]), close > 0 { return close }
        }
        throw QuoteError.emptyData
    }

    // --- 符号格式转换 ---

    private func normalizeForTencent(symbol: String, market: MarketType) -> String {
        let code = extractPureCode(symbol: symbol, market: market)
        switch market {
        case .cn:
            return code.hasPrefix("6") || code.hasPrefix("9") ? "sh\(code)" : "sz\(code)"
        case .hk:
            return "hk\(code)"
        case .us:
            return "us\(code)"
        }
    }

    private func normalizeForSina(symbol: String, market: MarketType) -> String {
        let code = extractPureCode(symbol: symbol, market: market)
        switch market {
        case .cn:
            return code.hasPrefix("6") || code.hasPrefix("9") ? "sh\(code)" : "sz\(code)"
        case .hk:
            return "hk\(code)"
        case .us:
            return "gb_\(code.lowercased())"
        }
    }

    // 从 "601988.SH" / "601988" 中提取纯数字/字母代码
    private func extractPureCode(symbol: String, market: MarketType) -> String {
        let trimmed = symbol.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        // 去掉 .SH / .SZ / .HK 等后缀
        if let dotIndex = trimmed.lastIndex(of: ".") {
            return String(trimmed[..<dotIndex])
        }
        return trimmed
    }

    func fetchDividendDetail(symbol: String, market: MarketType) async throws -> DividendDetailSnapshot {
        let yahooSymbol = normalizeForYahoo(symbol: symbol, market: market)
        let encoded = yahooSymbol.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)
        guard let encoded, !encoded.isEmpty else { throw QuoteError.invalidURL }

        guard let url = URL(string: "https://query1.finance.yahoo.com/v8/finance/chart/\(encoded)?range=11y&interval=1mo&includePrePost=false&events=div") else {
            throw QuoteError.invalidURL
        }

        let data = try await fetchYahooData(from: url)

        let decoded = try JSONDecoder().decode(YahooChartResponse.self, from: data)
        guard let first = decoded.chart.result?.first else {
            throw QuoteError.emptyData
        }

        let calendar = Calendar(identifier: .gregorian)
        let prices = zipPriceSeries(timestamps: first.timestamp ?? [], closes: first.indicators?.quote?.first?.close ?? [])
        let dividends = (first.events?.dividends ?? [:]).values.sorted { $0.date < $1.date }

        let ttmDividend = computeTTMDividend(dividends: dividends)
        let refPrice = first.meta.regularMarketPrice ??
            prices.last?.close ??
            first.meta.previousClose ??
            first.meta.chartPreviousClose ??
            0
        let currentYield = refPrice > 0 ? ttmDividend / refPrice : 0

        // 先建 10 年数据用于计算平均值，取后 5 年用于图表展示。
        let yearly10 = buildYearlyPoints(prices: prices, dividends: dividends, calendar: calendar, years: 10)
        let yearly5 = Array(yearly10.suffix(5))
        let quarterly = buildQuarterlyPoints(prices: prices, calendar: calendar, years: 5)

        let fiveYearAvgYield = averageYield(of: yearly5)
        let tenYearAvgYield = averageYield(of: yearly10)

        return DividendDetailSnapshot(
            latestDividendTTM: ttmDividend,
            currentDividendYield: currentYield,
            fiveYearAvgYield: fiveYearAvgYield,
            tenYearAvgYield: tenYearAvgYield,
            yearlyPoints: yearly5,
            quarterlyPoints: quarterly
        )
    }

    func fetchFxRatesToCNY(currencies: Set<String>) async -> [String: Double] {
        let normalized = Set(currencies.map { $0.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() })
        var result: [String: Double] = ["CNY": 1]
        let targets = normalized.filter { $0 != "CNY" }
        guard !targets.isEmpty else { return result }

        if let url = URL(string: "https://open.er-api.com/v6/latest/CNY"),
           let (data, response) = try? await URLSession.shared.data(for: yahooRequest(url: url)),
           let http = response as? HTTPURLResponse,
           (200 ... 299).contains(http.statusCode),
           let decoded = try? JSONDecoder().decode(ExchangeRateResponse.self, from: data) {
            for currency in targets {
                if let cnyToCurrency = decoded.rates[currency], cnyToCurrency > 0 {
                    result[currency] = 1 / cnyToCurrency
                }
            }
        }

        for currency in targets where result[currency] == nil {
            result[currency] = fallbackFxRateToCNY(for: currency)
        }
        return result
    }

    // 将时间戳与 close 数列对齐，过滤掉空值和非正数价格。
    private func zipPriceSeries(timestamps: [TimeInterval], closes: [Double?]) -> [(date: Date, close: Double)] {
        let count = min(timestamps.count, closes.count)
        guard count > 0 else { return [] }
        var output: [(date: Date, close: Double)] = []
        output.reserveCapacity(count)
        for index in 0 ..< count {
            guard let close = closes[index], close > 0 else { continue }
            output.append((Date(timeIntervalSince1970: timestamps[index]), close))
        }
        return output
    }

    // 计算近 12 个月每股分红总额（TTM）。
    private func computeTTMDividend(dividends: [YahooDividendEvent]) -> Double {
        let oneYearAgo = Date().addingTimeInterval(-365 * 24 * 60 * 60)
        return dividends.reduce(into: 0) { sum, event in
            let eventDate = Date(timeIntervalSince1970: event.date)
            if eventDate >= oneYearAgo {
                sum += max(0, event.amount)
            }
        }
    }

    // 计算有效年份的平均股息率（剔除股息为 0 的年份）。
    private func averageYield(of points: [DividendYearPoint]) -> Double {
        let validYields = points.map { $0.dividendYield }.filter { $0 > 0 }
        guard !validYields.isEmpty else { return 0 }
        return validYields.reduce(0, +) / Double(validYields.count)
    }

    // 构建最近 N 年股息点，缺失年份自动补零，保持图表连续。
    private func buildYearlyPoints(
        prices: [(date: Date, close: Double)],
        dividends: [YahooDividendEvent],
        calendar: Calendar,
        years: Int
    ) -> [DividendYearPoint] {
        let currentYear = calendar.component(.year, from: Date())
        let startYear = currentYear - years + 1

        var dividendsByYear: [Int: Double] = [:]
        for dividend in dividends {
            let year = calendar.component(.year, from: Date(timeIntervalSince1970: dividend.date))
            dividendsByYear[year, default: 0] += max(0, dividend.amount)
        }

        var lastCloseByYear: [Int: (date: Date, close: Double)] = [:]
        for point in prices {
            let year = calendar.component(.year, from: point.date)
            if let existing = lastCloseByYear[year], existing.date > point.date {
                continue
            }
            lastCloseByYear[year] = (point.date, point.close)
        }

        var output: [DividendYearPoint] = []
        for year in startYear ... currentYear {
            let dividend = dividendsByYear[year] ?? 0
            let close = lastCloseByYear[year]?.close ?? 0
            let dividendYield = close > 0 ? dividend / close : 0
            output.append(
                DividendYearPoint(
                    year: year,
                    dividendPerShare: dividend,
                    dividendYield: dividendYield,
                    closePrice: close
                )
            )
        }
        return output
    }

    // 构建最近 N 年季度收盘价序列，用于股息详情里的价格曲线。
    private func buildQuarterlyPoints(
        prices: [(date: Date, close: Double)],
        calendar: Calendar,
        years: Int
    ) -> [QuarterlyPricePoint] {
        let currentYear = calendar.component(.year, from: Date())
        let startYear = currentYear - years + 1
        var quarterMap: [String: (date: Date, close: Double, year: Int, quarter: Int)] = [:]

        for point in prices {
            let year = calendar.component(.year, from: point.date)
            guard year >= startYear else { continue }
            let month = calendar.component(.month, from: point.date)
            let quarter = ((month - 1) / 3) + 1
            let key = "\(year)-Q\(quarter)"
            if let existing = quarterMap[key], existing.date > point.date {
                continue
            }
            quarterMap[key] = (point.date, point.close, year, quarter)
        }

        return quarterMap.values
            .sorted { lhs, rhs in
                if lhs.year == rhs.year {
                    return lhs.quarter < rhs.quarter
                }
                return lhs.year < rhs.year
            }
            .map { item in
                QuarterlyPricePoint(
                    year: item.year,
                    quarter: item.quarter,
                    label: "\(item.year) Q\(item.quarter)",
                    closePrice: item.close
                )
            }
    }

    private func fallbackFxRateToCNY(for currency: String) -> Double {
        switch currency {
        case "USD":
            return 7.2
        case "HKD":
            return 0.92
        default:
            return 1
        }
    }

    // 股票搜索：通过 Yahoo Finance 搜索接口提供候选。
    func searchStocks(query: String) async -> [StockSearchResult] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty,
              let encoded = trimmed.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "https://query2.finance.yahoo.com/v1/finance/search?q=\(encoded)&quotesCount=8&newsCount=0&enableFuzzyQuery=false&quotesQueryId=tss_match_phrase_query")
        else { return [] }

        guard let data = try? await fetchYahooData(from: url),
              let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let quotes = root["quotes"] as? [[String: Any]]
        else { return [] }

        return quotes.compactMap { item in
            guard let symbol = item["symbol"] as? String,
                  let quoteType = item["quoteType"] as? String,
                  quoteType == "EQUITY"
            else { return nil }
            let name = (item["longname"] as? String) ?? (item["shortname"] as? String) ?? symbol
            let exchange = (item["exchange"] as? String) ?? ""
            return StockSearchResult(symbol: symbol, name: name, exchange: exchange)
        }
    }

    // 统一符号格式，确保 CN/HK/US 都能命中 Yahoo 接口。
    private func normalizeForYahoo(symbol: String, market: MarketType) -> String {
        let trimmed = symbol.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        switch market {
        case .cn:
            if trimmed.hasSuffix(".SH") {
                return trimmed.replacingOccurrences(of: ".SH", with: ".SS")
            }
            if trimmed.hasSuffix(".SZ") {
                return trimmed
            }
            if trimmed.count == 6, Int(trimmed) != nil {
                return trimmed.hasPrefix("6") ? "\(trimmed).SS" : "\(trimmed).SZ"
            }
            return trimmed
        case .hk:
            if trimmed.hasSuffix(".HK") {
                return trimmed
            }
            if Int(trimmed) != nil {
                let padded = String(repeating: "0", count: max(0, 5 - trimmed.count)) + trimmed
                return "\(padded).HK"
            }
            return trimmed
        case .us:
            return trimmed.replacingOccurrences(of: "_", with: "-")
        }
    }
}

private struct YahooChartResponse: Decodable {
    let chart: YahooChartContainer
}

private struct YahooChartContainer: Decodable {
    let result: [YahooChartResult]?
}

private struct YahooChartResult: Decodable {
    let meta: YahooChartMeta
    let timestamp: [TimeInterval]?
    let indicators: YahooIndicators?
    let events: YahooEvents?
}

private struct YahooChartMeta: Decodable {
    let regularMarketPrice: Double?
    let previousClose: Double?
    let chartPreviousClose: Double?
}

private struct YahooIndicators: Decodable {
    let quote: [YahooQuoteIndicator]?
}

private struct YahooQuoteIndicator: Decodable {
    let close: [Double?]?
}

private struct YahooEvents: Decodable {
    let dividends: [String: YahooDividendEvent]?
}

private struct YahooDividendEvent: Decodable {
    let amount: Double
    let date: TimeInterval
}

private struct ExchangeRateResponse: Decodable {
    let rates: [String: Double]
}
