import axios from 'axios'

import type {
  CreateStockPayload,
  CreateTransactionPayload,
  DividendDetail,
  PortfolioBackupData,
  PortfolioImportResult,
  PortfolioSummary,
  StockSearchItem,
  StockSearchResponse,
  StockListResponse,
  StockRow,
  TransactionDetail
} from '../types'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000
})

// API 层只做请求和返回值约束，页面逻辑放在组件里处理。
export async function fetchSummary(): Promise<PortfolioSummary> {
  const { data } = await client.get<PortfolioSummary>('/summary')
  return data
}

export async function fetchStocks(): Promise<StockListResponse> {
  const { data } = await client.get<StockListResponse>('/stocks')
  return data
}

export async function searchStocks(query: string): Promise<StockSearchItem[]> {
  const { data } = await client.get<StockSearchResponse>('/stocks/search', {
    params: { q: query, limit: 20 }
  })
  return data.items
}

export async function createStock(payload: CreateStockPayload): Promise<StockRow> {
  const { data } = await client.post<StockRow>('/stocks', payload)
  return data
}

export async function createTransaction(stockId: number, payload: CreateTransactionPayload): Promise<StockRow> {
  const { data } = await client.post<StockRow>(`/stocks/${stockId}/transactions`, payload)
  return data
}

export async function fetchTransactionDetail(stockId: number): Promise<TransactionDetail> {
  const { data } = await client.get<TransactionDetail>(`/stocks/${stockId}/transactions`)
  return data
}

export async function fetchDividendDetail(stockId: number): Promise<DividendDetail> {
  const { data } = await client.get<DividendDetail>(`/stocks/${stockId}/dividends`)
  return data
}

export async function refreshStock(stockId: number): Promise<StockRow> {
  const { data } = await client.post<StockRow>(`/stocks/${stockId}/refresh`)
  return data
}

export async function refreshAllStocks(): Promise<void> {
  await client.post('/refresh')
}

export async function deleteStock(stockId: number): Promise<void> {
  await client.delete(`/stocks/${stockId}`)
}

export async function exportPortfolioData(): Promise<PortfolioBackupData> {
  const { data } = await client.get<PortfolioBackupData>('/portfolio/export')
  return data
}

export async function exportPortfolioExcel(): Promise<Blob> {
  const { data } = await client.get('/portfolio/export.xlsx', { responseType: 'blob' })
  return data
}

export async function importPortfolioData(payload: PortfolioBackupData): Promise<PortfolioImportResult> {
  const { data } = await client.post<PortfolioImportResult>('/portfolio/import', payload)
  return data
}
