<script setup lang="ts">
import type { PortfolioSummary } from '../types'
import { formatMoney, formatPercent } from '../utils/format'

defineProps<{
  summary: PortfolioSummary | null
}>()
</script>

<template>
  <!-- 顶部卡片只展示组合级关键信息，避免首页信息过载。 -->
  <section class="summary-grid">
    <div class="summary-card">
      <div class="summary-card__label">持仓总市值</div>
      <div class="summary-card__value">
        {{ formatMoney(summary?.total_market_value ?? 0, summary?.base_currency ?? 'CNY') }}
      </div>
      <div class="summary-card__hint">组合汇总按 {{ summary?.base_currency ?? 'CNY' }} 估算</div>
    </div>

    <div class="summary-card accent-card">
      <div class="summary-card__label">每年预计总分红</div>
      <div class="summary-card__value">
        {{ formatMoney(summary?.total_annual_dividend ?? 0, summary?.base_currency ?? 'CNY') }}
      </div>
      <div class="summary-card__hint">基于最新 TTM 每股分红与持仓股数</div>
    </div>

    <div class="summary-card">
      <div class="summary-card__label">组合整体股息率</div>
      <div class="summary-card__value">{{ formatPercent(summary?.overall_dividend_yield ?? 0) }}</div>
      <div class="summary-card__hint">已纳入 {{ summary?.stock_count ?? 0 }} 只股票</div>
    </div>
  </section>
</template>
