<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import AddStockDialog from './components/AddStockDialog.vue'
import AddTransactionDialog from './components/AddTransactionDialog.vue'
import DividendsDrawer from './components/DividendsDrawer.vue'
import StockTable from './components/StockTable.vue'
import SummaryCards from './components/SummaryCards.vue'
import TopMenuBar from './components/TopMenuBar.vue'
import TransactionsDrawer from './components/TransactionsDrawer.vue'
import {
  createStock,
  createTransaction,
  deleteStock,
  exportPortfolioData,
  exportPortfolioExcel,
  fetchDividendDetail,
  fetchStocks,
  fetchSummary,
  fetchTransactionDetail,
  importPortfolioData
} from './api/client'
import type {
  CreateStockPayload,
  CreateTransactionPayload,
  DividendDetail,
  PortfolioBackupData,
  PortfolioSummary,
  StockRow,
  TransactionDetail
} from './types'

// 页面级状态统一放在根组件，避免多个弹窗之间互相抢数据。
const loading = ref(false)
const actionLoading = ref(false)
const detailLoading = ref(false)
const backupLoading = ref(false)

const summary = ref<PortfolioSummary | null>(null)
const stocks = ref<StockRow[]>([])
const baseCurrency = computed(() => summary.value?.base_currency || 'CNY')

const addStockVisible = ref(false)
const addTransactionVisible = ref(false)
const transactionsVisible = ref(false)
const dividendsVisible = ref(false)

const activeStock = ref<StockRow | null>(null)
const transactionMode = ref<'buy' | 'sell'>('buy')
const transactionDetail = ref<TransactionDetail | null>(null)
const dividendDetail = ref<DividendDetail | null>(null)
const importInputRef = ref<HTMLInputElement | null>(null)
type DataToolCommand = 'export_excel' | 'export_json' | 'import_json'

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function waitForPortfolioSync(maxAttempts = 8, intervalMs = 2000) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await delay(intervalMs)
    await loadDashboard()
    if (!stocks.value.some((item) => item.sync_status === 'pending')) {
      break
    }
  }
}

async function loadDashboard() {
  // 首页需要同时拿汇总和持仓列表，失败时统一给用户提示。
  loading.value = true
  try {
    const [summaryData, stocksData] = await Promise.all([fetchSummary(), fetchStocks()])
    summary.value = summaryData
    stocks.value = stocksData.items
  } catch {
    ElMessage.error('加载首页数据失败，请检查后端服务或网络')
  } finally {
    loading.value = false
  }
}

async function handleCreateStock(payload: CreateStockPayload) {
  actionLoading.value = true
  try {
    await createStock(payload)
    addStockVisible.value = false
    await loadDashboard()
    void waitForPortfolioSync()
    ElMessage.success('持仓已添加，缓存正在后台同步')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '添加持仓失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleCreateTransaction(payload: CreateTransactionPayload) {
  if (!activeStock.value) return
  actionLoading.value = true
  try {
    await createTransaction(activeStock.value.id, payload)
    addTransactionVisible.value = false
    await loadDashboard()
    void waitForPortfolioSync()
    ElMessage.success(payload.transaction_type === 'buy' ? '买入记录已保存，缓存正在后台同步' : '卖出记录已保存，缓存正在后台同步')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || `${payload.transaction_type === 'buy' ? '买入' : '卖出'}失败`)
  } finally {
    actionLoading.value = false
  }
}

async function handleOpenTransactions(stock: StockRow) {
  activeStock.value = stock
  transactionsVisible.value = true
  detailLoading.value = true
  transactionDetail.value = null
  try {
    transactionDetail.value = await fetchTransactionDetail(stock.id)
  } catch {
    ElMessage.error('加载持仓详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleOpenDividends(stock: StockRow) {
  activeStock.value = stock
  dividendsVisible.value = true
  detailLoading.value = true
  dividendDetail.value = null
  try {
    dividendDetail.value = await fetchDividendDetail(stock.id)
  } catch {
    ElMessage.error('加载股息详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleDeleteStock(stock: StockRow) {
  try {
    await ElMessageBox.confirm(`确认删除 ${stock.name}（${stock.normalized_symbol}）及其所有交易记录吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  actionLoading.value = true
  try {
    await deleteStock(stock.id)
    await loadDashboard()
    ElMessage.success('股票已删除')
  } catch {
    ElMessage.error('删除失败')
  } finally {
    actionLoading.value = false
  }
}

function openBuyDialog(stock: StockRow) {
  activeStock.value = stock
  transactionMode.value = 'buy'
  addTransactionVisible.value = true
}

function openSellDialog(stock: StockRow) {
  activeStock.value = stock
  transactionMode.value = 'sell'
  addTransactionVisible.value = true
}

function backupFilename(ext: 'json' | 'xlsx', prefix = 'yield-ledger-backup') {
  // 导出文件名带时间戳，方便多版本留档。
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${prefix}-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}.${ext}`
}

async function handleExportExcel() {
  backupLoading.value = true
  try {
    const data = await exportPortfolioExcel()
    const url = URL.createObjectURL(data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = backupFilename('xlsx', 'yield-ledger-export')
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Excel 导出成功')
  } catch {
    ElMessage.error('Excel 导出失败，请稍后重试')
  } finally {
    backupLoading.value = false
  }
}

async function handleExportJsonBackup() {
  backupLoading.value = true
  try {
    const data = await exportPortfolioData()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = backupFilename('json')
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success('JSON 备份导出成功')
  } catch {
    ElMessage.error('JSON 备份导出失败，请稍后重试')
  } finally {
    backupLoading.value = false
  }
}

function triggerImportPicker() {
  importInputRef.value?.click()
}

async function handleDataToolCommand(command: DataToolCommand) {
  if (command === 'export_excel') {
    await handleExportExcel()
    return
  }
  if (command === 'export_json') {
    await handleExportJsonBackup()
    return
  }
  triggerImportPicker()
}

async function handleImportFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  let parsed: PortfolioBackupData
  try {
    const text = await file.text()
    parsed = JSON.parse(text)
  } catch {
    ElMessage.error('导入文件不是有效的 JSON')
    return
  }

  if (!parsed || !Array.isArray(parsed.stocks)) {
    ElMessage.error('导入文件缺少 stocks 数组')
    return
  }

  const mode = parsed.mode === 'merge' ? 'merge' : 'replace'
  try {
    await ElMessageBox.confirm(
      mode === 'replace'
        ? `将覆盖当前全部持仓并导入 ${parsed.stocks.length} 只股票，是否继续？`
        : `将合并导入 ${parsed.stocks.length} 只股票（同代码会覆盖），是否继续？`,
      '导入确认',
      {
        type: 'warning',
        confirmButtonText: '导入',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  backupLoading.value = true
  try {
    const result = await importPortfolioData({
      mode,
      version: parsed.version,
      stocks: parsed.stocks
    })
    await loadDashboard()
    ElMessage.success(`导入成功：${result.imported_stocks} 只股票 / ${result.imported_transactions} 条交易`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '导入失败，请检查文件内容')
  } finally {
    backupLoading.value = false
  }
}

onMounted(() => {
  void loadDashboard()
})
</script>

<template>
  <div class="page-shell">
    <TopMenuBar />

    <header class="hero">
      <div>
        <p class="eyebrow">Yield Ledger</p>
        <h1>息流账本</h1>
        <p class="hero__desc">录入买入或卖出交易后立即重算持仓，并同步最新价格与分红缓存。组合汇总默认按 {{ baseCurrency }} 估算。</p>
      </div>
    </header>

    <SummaryCards :summary="summary" />

    <StockTable
      :stocks="stocks"
      :loading="loading"
      :base-currency="baseCurrency"
      @buy-stock="openBuyDialog"
      @sell-stock="openSellDialog"
      @view-transactions="handleOpenTransactions"
      @view-dividends="handleOpenDividends"
      @delete-stock="handleDeleteStock"
    >
      <template #actions>
        <div class="table-actions">
          <el-button type="primary" :icon="Plus" @click="addStockVisible = true">添加持仓</el-button>
          <el-dropdown
            trigger="click"
            :disabled="backupLoading"
            @command="(command) => handleDataToolCommand(command as DataToolCommand)"
          >
            <el-button plain :loading="backupLoading">导入/导出</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export_excel">导出 Excel</el-dropdown-item>
                <el-dropdown-item command="export_json">导出备份 JSON</el-dropdown-item>
                <el-dropdown-item command="import_json">导入 JSON</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <input
            ref="importInputRef"
            class="hidden-file-input"
            type="file"
            accept=".json,application/json"
            @change="handleImportFileChange"
          />
        </div>
      </template>
    </StockTable>

    <AddStockDialog v-model="addStockVisible" :loading="actionLoading" @submit="handleCreateStock" />

    <AddTransactionDialog
      v-model="addTransactionVisible"
      :loading="actionLoading"
      :stock="activeStock"
      :mode="transactionMode"
      @submit="handleCreateTransaction"
    />

    <TransactionsDrawer v-model="transactionsVisible" :detail="transactionDetail" :loading="detailLoading" />

    <DividendsDrawer v-model="dividendsVisible" :detail="dividendDetail" :loading="detailLoading" />
  </div>
</template>
