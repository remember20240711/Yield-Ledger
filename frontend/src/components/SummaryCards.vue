<script setup lang="ts">
import type { PortfolioSummary } from '../types'
import { formatMoney, formatPercent } from '../utils/format'

defineProps<{
  summary: PortfolioSummary | null
}>()
</script>

<template>
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
          <strong>{{ formatMoney(summary?.total_latest_full_year_dividend ?? 0, summary?.base_currency ?? 'CNY') }}</strong>
          <span>上一年分红</span>
        </div>
      </div>

      <div class="summary-metric">
        <span class="summary-metric__icon">¥</span>
        <div class="summary-metric__body">
          <strong>{{ formatMoney(summary?.total_annual_dividend ?? 0, summary?.base_currency ?? 'CNY') }}</strong>
          <span>TTM分红</span>
        </div>
      </div>

      <div class="summary-metric">
        <span class="summary-metric__icon">%</span>
        <div class="summary-metric__body">
          <strong>{{ formatPercent(summary?.overall_latest_full_year_yield ?? 0) }}</strong>
          <span>上一年股息率</span>
        </div>
      </div>

      <div class="summary-metric">
        <span class="summary-metric__icon">%</span>
        <div class="summary-metric__body">
          <strong>{{ formatPercent(summary?.overall_dividend_yield ?? 0) }}</strong>
          <span>TTM 组合股息率</span>
        </div>
      </div>
    </div>
  </section>
</template>
