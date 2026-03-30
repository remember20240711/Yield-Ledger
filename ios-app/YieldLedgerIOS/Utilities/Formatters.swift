import Foundation

enum AppFormatters {
    // 统一金额格式，保证展示稳定。
    static func money(_ value: Double, currencyCode: String) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = currencyCode.uppercased()
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }

    static func number(_ value: Double, digits: Int = 2) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = digits
        formatter.minimumFractionDigits = digits
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }

    static func percent(_ value: Double, digits: Int = 2) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .percent
        formatter.maximumFractionDigits = digits
        formatter.minimumFractionDigits = digits
        return formatter.string(from: NSNumber(value: value)) ?? "\(value * 100)%"
    }

    // 股数：整数时省略小数，碎股时保留最多 4 位有效小数。
    static func shares(_ value: Double) -> String {
        if value == floor(value) {
            return String(Int(value))
        }
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = 4
        formatter.minimumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    }
}
