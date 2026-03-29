export function formatMoney(value: number, currency: string): string {
  // 页面金额展示统一走 Intl，避免各组件自己拼货币符号。
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value || 0)
}

export function formatPrice(value: number, currency: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 4,
    minimumFractionDigits: 2
  }).format(value || 0)
}

export function formatTradePrice(value: number, currency: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value || 0)
}

export function formatPercent(value: number): string {
  return `${(value || 0).toFixed(2)}%`
}

export function formatShares(value: number): string {
  return (value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4
  })
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return '未同步'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

export function marketLabel(market: string): string {
  if (market === 'CN') return 'A股'
  if (market === 'HK') return '港股'
  if (market === 'US') return '美股'
  return market
}
