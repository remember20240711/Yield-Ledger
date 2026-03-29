import Foundation

protocol QuoteProviding {
    func fetchLatestPrice(symbol: String, market: MarketType) async throws -> Double
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

// iOS 客户端直接走公开 Yahoo 行情接口，不依赖自建后端。
final class YahooQuoteService: QuoteProviding {
    func fetchLatestPrice(symbol: String, market: MarketType) async throws -> Double {
        let yahooSymbol = normalizeForYahoo(symbol: symbol, market: market)
        let encoded = yahooSymbol.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)
        guard let encoded, !encoded.isEmpty else {
            throw QuoteError.invalidURL
        }

        let endpoint = "https://query1.finance.yahoo.com/v8/finance/chart/\(encoded)?range=1d&interval=1d&includePrePost=false&events=div"
        guard let url = URL(string: endpoint) else {
            throw QuoteError.invalidURL
        }

        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw QuoteError.invalidResponse
        }
        guard !data.isEmpty else {
            throw QuoteError.emptyData
        }

        let decoded = try JSONDecoder().decode(YahooChartResponse.self, from: data)
        guard let first = decoded.chart.result?.first else {
            throw QuoteError.emptyData
        }
        if let price = first.meta.regularMarketPrice {
            return price
        }
        if let close = first.meta.previousClose {
            return close
        }
        if let close = first.meta.chartPreviousClose {
            return close
        }
        throw QuoteError.emptyData
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
}

private struct YahooChartMeta: Decodable {
    let regularMarketPrice: Double?
    let previousClose: Double?
    let chartPreviousClose: Double?
}

