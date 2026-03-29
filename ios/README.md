# Yield Ledger iOS

这是一个纯客户端版本的 iOS 工程，不依赖你自建服务器。  
本地数据使用 `SwiftData`（底层 SQLite）持久化。

## 刷新策略（按你的要求）

- App 启动时：联网刷新当前持仓股价
- App 切回前台时：联网刷新当前持仓股价
- 添加新持仓后：只刷新该标的股价
- 买入/卖出时：只更新本地交易数据，不强制联网

## 工程位置

- Xcode 工程：`ios/YieldLedgerIOS.xcodeproj`
- 生成配置：`ios/project.yml`（可用 `xcodegen generate` 重新生成）

## 本地运行

1. 安装并打开 Xcode
2. 双击打开 `ios/YieldLedgerIOS.xcodeproj`
3. 选择 Team（签名）
4. 选择模拟器或真机，点击 Run

## 备注

当前行情接口使用 Yahoo 公网接口（`query1.finance.yahoo.com`）。  
如果后续你想切到其他数据源，只需要替换 `QuoteService.swift`。

