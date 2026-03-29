<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

import type { DividendDetail } from '../types'
import { formatMoney, formatPercent } from '../utils/format'

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent])

const props = defineProps<{
  modelValue: boolean
  detail: DividendDetail | null
  loading: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

// 图表只展示最近五年，避免长历史把趋势压得太平。
const recentDividends = computed(() => (props.detail?.dividends ?? []).slice(-5))

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    valueFormatter: (value: number) => formatPercent(value || 0)
  },
  grid: {
    left: 40,
    right: 24,
    top: 24,
    bottom: 30
  },
  xAxis: {
    type: 'category',
    data: recentDividends.value.map((item) => String(item.year))
  },
  yAxis: {
    type: 'value',
    name: '股息率',
    axisLabel: {
      formatter: '{value}%'
    }
  },
  series: [
    {
      name: '股息率',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      itemStyle: { color: '#0f766e' },
      areaStyle: {
        color: 'rgba(15, 118, 110, 0.12)'
      },
      lineStyle: {
        width: 3,
        color: '#0f766e'
      },
      data: recentDividends.value.map((item) => item.dividend_yield)
    }
  ]
}))
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="最近五年股息率"
    width="min(960px, calc(100vw - 24px))"
    @close="emit('update:modelValue', false)"
  >
    <div v-loading="loading">
      <template v-if="detail">
        <div class="drawer-head">
          <div>
            <div class="drawer-head__title">{{ detail.name }}</div>
            <div class="drawer-head__sub">{{ detail.symbol }}</div>
          </div>
          <div class="drawer-yield">
            <span>当前股息率(TTM)</span>
            <strong>{{ formatPercent(detail.current_dividend_yield) }}</strong>
          </div>
        </div>

        <div v-if="recentDividends.length" class="chart-panel">
          <v-chart :option="chartOption" autoresize style="height: 320px" />
        </div>
        <el-empty v-else description="暂无年度股息数据" />

        <el-table v-if="recentDividends.length" :data="recentDividends" stripe>
          <el-table-column prop="year" label="年份" min-width="100" />
          <el-table-column label="每股分红" min-width="180">
            <template #default="{ row }">{{ formatMoney(row.dividend_per_share, detail.currency) }}</template>
          </el-table-column>
          <el-table-column label="股息率" min-width="140">
            <template #default="{ row }">{{ formatPercent(row.dividend_yield) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无年度股息数据" />
      </template>
    </div>
  </el-dialog>
</template>
