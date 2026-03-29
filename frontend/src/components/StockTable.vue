<script setup lang="ts">
import type { StockRow } from '../types'
import {
  formatMoney,
  formatPercent,
  formatShares,
  formatTradePrice
} from '../utils/format'

defineProps<{
  stocks: StockRow[]
  loading: boolean
  baseCurrency: string
}>()

const emit = defineEmits<{
  (event: 'buy-stock', stock: StockRow): void
  (event: 'sell-stock', stock: StockRow): void
  (event: 'view-transactions', stock: StockRow): void
  (event: 'view-dividends', stock: StockRow): void
  (event: 'delete-stock', stock: StockRow): void
}>()

function displayCurrentPrice(price: number, currency: string): string {
  // 没有缓存价时明确显示空值，避免误读成 0。
  return price > 0 ? formatTradePrice(price, currency) : '—'
}
</script>

<template>
  <section class="panel">
    <div class="panel__head">
      <div>
        <h2>股票持仓列表</h2>
        <p>当前股价与分红缓存会自动刷新，市值/成本/盈亏按 {{ baseCurrency }} 汇总估算。</p>
      </div>
      <div class="panel__actions">
        <slot name="actions" />
      </div>
    </div>

    <div class="desktop-table" v-loading="loading">
      <el-table :data="stocks" stripe style="width: 100%">
        <el-table-column label="股票代码" min-width="130" fixed="left">
          <template #default="{ row }">
            <strong>{{ row.normalized_symbol }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="股票名称" min-width="180" />
        <el-table-column label="当前股息率" min-width="120">
          <template #default="{ row }">
            <el-button link type="primary" class="yield-link" @click="emit('view-dividends', row)">
              {{ formatPercent(row.current_dividend_yield) }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="预计每年分红" min-width="150">
          <template #default="{ row }">{{ formatMoney(row.annual_dividend, row.base_currency) }}</template>
        </el-table-column>
        <el-table-column label="当前持仓数量" min-width="120">
          <template #default="{ row }">{{ formatShares(row.total_shares) }}</template>
        </el-table-column>
        <el-table-column label="当前股价 / 成本价" min-width="140">
          <template #default="{ row }">
            <div class="stacked-price">
              <span>{{ displayCurrentPrice(row.current_price, row.currency) }}</span>
              <span>{{ formatTradePrice(row.average_cost, row.currency) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="当前持仓市值" min-width="160">
          <template #default="{ row }">{{ formatMoney(row.market_value, row.base_currency) }}</template>
        </el-table-column>
        <el-table-column label="盈亏" min-width="150">
          <template #default="{ row }">
            <span :class="row.profit_loss >= 0 ? 'profit' : 'loss'">
              {{ formatMoney(row.profit_loss, row.base_currency) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-stack">
              <div class="action-group">
                <el-button size="small" type="primary" @click="emit('buy-stock', row)">买入</el-button>
                <el-button size="small" type="warning" plain @click="emit('sell-stock', row)">卖出</el-button>
              </div>
              <div class="action-group action-group--minor">
                <el-button size="small" text @click="emit('view-transactions', row)">持仓详情</el-button>
                <el-button size="small" text class="action-danger" @click="emit('delete-stock', row)">删除</el-button>
              </div>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="mobile-cards" v-loading="loading">
      <article v-for="stock in stocks" :key="stock.id" class="stock-card">
        <div class="stock-card__head">
          <div>
            <h3>{{ stock.name }}</h3>
            <p>{{ stock.normalized_symbol }}</p>
          </div>
        </div>

        <div class="stock-card__grid">
          <div>
            <span>当前股息率</span>
            <strong>
              <el-button link type="primary" class="yield-link" @click="emit('view-dividends', stock)">
                {{ formatPercent(stock.current_dividend_yield) }}
              </el-button>
            </strong>
          </div>
          <div>
            <span>预计每年分红</span>
            <strong>{{ formatMoney(stock.annual_dividend, stock.base_currency) }}</strong>
          </div>
          <div>
            <span>当前持仓数量</span>
            <strong>{{ formatShares(stock.total_shares) }}</strong>
          </div>
          <div>
            <span>当前股价 / 成本价</span>
            <strong class="stacked-price">
              <span>{{ displayCurrentPrice(stock.current_price, stock.currency) }}</span>
              <span>{{ formatTradePrice(stock.average_cost, stock.currency) }}</span>
            </strong>
          </div>
          <div>
            <span>当前持仓市值</span>
            <strong>{{ formatMoney(stock.market_value, stock.base_currency) }}</strong>
          </div>
          <div>
            <span>盈亏</span>
            <strong :class="stock.profit_loss >= 0 ? 'profit' : 'loss'">
              {{ formatMoney(stock.profit_loss, stock.base_currency) }}
            </strong>
          </div>
        </div>

        <div class="stock-card__foot">
          <div class="action-stack">
            <div class="action-group">
              <el-button size="small" type="primary" @click="emit('buy-stock', stock)">买入</el-button>
              <el-button size="small" type="warning" plain @click="emit('sell-stock', stock)">卖出</el-button>
            </div>
            <div class="action-group action-group--minor">
              <el-button size="small" text @click="emit('view-transactions', stock)">持仓详情</el-button>
              <el-button size="small" text class="action-danger" @click="emit('delete-stock', stock)">删除</el-button>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
