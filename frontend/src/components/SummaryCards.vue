<script setup lang="ts">
import type { PortfolioSummary } from '../types'
import { formatMoney, formatPercent } from '../utils/format'

defineProps<{
  summary: PortfolioSummary | null
}>()
</script>

<template>
  <!-- 顶部汇总改成 iOS 同款 Hero 卡片，信息集中、层次更清晰。 -->
  <section class="summary-hero">
    <div class="summary-hero__main">
      <div class="summary-hero__eyebrow">Portfolio Overview</div>
      <div class="summary-hero__label">持仓总市值</div>
      <div class="summary-hero__value">
        {{ formatMoney(summary?.total_market_value ?? 0, summary?.base_currency ?? 'CNY') }}
      </div>
    </div>

    <div class="summary-hero__metrics">
      <div class="summary-metric">
        <span class="summary-metric__icon">¥</span>
        <div class="summary-metric__body">
          <strong>{{ formatMoney(summary?.total_annual_dividend ?? 0, summary?.base_currency ?? 'CNY') }}</strong>
          <span>年预计分红</span>
        </div>
      </div>

      <div class="summary-metric">
        <span class="summary-metric__icon">%</span>
        <div class="summary-metric__body">
          <strong>{{ formatPercent(summary?.overall_dividend_yield ?? 0) }}</strong>
          <span>组合股息率</span>
        </div>
      </div>

      <div class="summary-metric">
        <span class="summary-metric__icon">#</span>
        <div class="summary-metric__body">
          <strong>{{ summary?.stock_count ?? 0 }} 只</strong>
          <span>持仓数量</span>
        </div>
      </div>
    </div>
  </section>
</template>
