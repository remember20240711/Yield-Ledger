<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";

import type { DividendDetail } from "../types";
import { formatMoney, formatPercent } from "../utils/format";

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

const props = defineProps<{
  modelValue: boolean;
  detail: DividendDetail | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: boolean): void;
}>();

// 只展示最近五年年度股息，保持图表简洁。
const recentDividends = computed(() =>
  (props.detail?.dividends ?? []).slice(-5),
);

// 价格图展示最近 20 个季度，贴近 iOS 的“趋势而不是噪声”逻辑。
const recentQuarterlyPrices = computed(() =>
  (props.detail?.quarterly_prices ?? []).slice(-20),
);

const fiveYearAvgYield = computed(() => {
  if (!recentDividends.value.length) return 0;
  const total = recentDividends.value.reduce(
    (sum, item) => sum + item.dividend_yield,
    0,
  );
  return total / recentDividends.value.length;
});

const latestQuarterPrice = computed(() => {
  const latest =
    recentQuarterlyPrices.value[recentQuarterlyPrices.value.length - 1];
  return latest?.close_price ?? 0;
});

const yieldChartOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    valueFormatter: (value: number) => formatPercent(value || 0),
  },
  grid: {
    left: 52,
    right: 24,
    top: 28,
    bottom: 24,
  },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: recentDividends.value.map((item) => String(item.year)),
    axisLine: {
      lineStyle: { color: "rgba(15, 23, 42, 0.18)" },
    },
  },
  yAxis: {
    type: "value",
    name: "股息率",
    axisLabel: {
      formatter: "{value}%",
    },
    splitLine: {
      lineStyle: { color: "rgba(148, 163, 184, 0.18)" },
    },
  },
  series: [
    {
      name: "股息率",
      type: "line",
      smooth: true,
      symbolSize: 8,
      itemStyle: { color: "#0f766e" },
      areaStyle: {
        color: "rgba(15, 118, 110, 0.14)",
      },
      lineStyle: {
        width: 3,
        color: "#0f766e",
      },
      data: recentDividends.value.map((item) => item.dividend_yield),
    },
  ],
}));

const priceChartOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    valueFormatter: (value: number) =>
      formatMoney(value || 0, props.detail?.currency || "CNY"),
  },
  grid: {
    left: 52,
    right: 24,
    top: 28,
    bottom: 24,
  },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: recentQuarterlyPrices.value.map((item) => item.label),
    axisLabel: {
      hideOverlap: true,
    },
    axisLine: {
      lineStyle: { color: "rgba(15, 23, 42, 0.18)" },
    },
  },
  yAxis: {
    type: "value",
    name: "价格",
    splitLine: {
      lineStyle: { color: "rgba(148, 163, 184, 0.18)" },
    },
  },
  series: [
    {
      name: "季度收盘价",
      type: "line",
      smooth: true,
      symbol: "none",
      itemStyle: { color: "#f59e0b" },
      areaStyle: {
        color: "rgba(245, 158, 11, 0.14)",
      },
      lineStyle: {
        width: 3,
        color: "#f59e0b",
      },
      data: recentQuarterlyPrices.value.map((item) => item.close_price),
    },
  ],
}));
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="股息详情"
    width="min(1040px, calc(100vw - 24px))"
    class="detail-dialog"
    @close="emit('update:modelValue', false)"
  >
    <div class="detail-sheet" v-loading="loading">
      <template v-if="detail">
        <section class="detail-header-card">
          <div class="detail-header-card__top">
            <div>
              <div class="detail-header-card__title">{{ detail.name }}</div>
              <div class="detail-header-card__sub">{{ detail.symbol }}</div>
            </div>
            <div class="detail-header-card__yield">
              <span>上一年股息率({{ detail.latest_full_year }})</span>
              <strong>{{
                formatPercent(detail.latest_full_year_dividend_yield)
              }}</strong>
            </div>
          </div>

          <div class="detail-pill-row">
            <div class="detail-pill">
              <span>上一年每股分红</span>
              <strong>{{
                formatMoney(detail.latest_full_year_dividend, detail.currency)
              }}</strong>
            </div>
            <div class="detail-pill">
              <span>当前股息率(TTM)</span>
              <strong>{{
                formatPercent(detail.current_dividend_yield)
              }}</strong>
            </div>
            <div class="detail-pill">
              <span>TTM 每股分红</span>
              <strong>{{
                formatMoney(detail.latest_dividend_ttm, detail.currency)
              }}</strong>
            </div>
            <div class="detail-pill">
              <span>5年平均股息率</span>
              <strong>{{ formatPercent(fiveYearAvgYield) }}</strong>
            </div>
            <div class="detail-pill">
              <span>最新季度价格</span>
              <strong>{{
                latestQuarterPrice > 0
                  ? formatMoney(latestQuarterPrice, detail.currency)
                  : "—"
              }}</strong>
            </div>
          </div>
        </section>

        <section v-if="recentDividends.length" class="detail-section">
          <div class="detail-section__head">
            <h3>最近五年股息率</h3>
            <p>按自然年聚合，例如 2025 年表示 2025-01-01 至 2025-12-31。</p>
          </div>
          <v-chart
            :option="yieldChartOption"
            autoresize
            style="height: 280px"
          />
        </section>

        <section v-if="recentQuarterlyPrices.length" class="detail-section">
          <div class="detail-section__head">
            <h3>最近五年季度收盘价</h3>
            <p>按季度粒度展示价格走势，和 iOS 版保持一致。</p>
          </div>
          <v-chart
            :option="priceChartOption"
            autoresize
            style="height: 260px"
          />
        </section>

        <section v-if="recentDividends.length" class="detail-section">
          <div class="detail-section__head">
            <h3>年度明细</h3>
            <p>查看年度分红、股息率和年末价格。</p>
          </div>

          <el-table :data="recentDividends" stripe class="detail-table">
            <el-table-column prop="year" label="年份" min-width="100" />
            <el-table-column label="每股分红" min-width="180">
              <template #default="{ row }">{{
                formatMoney(row.dividend_per_share, detail.currency)
              }}</template>
            </el-table-column>
            <el-table-column label="股息率" min-width="140">
              <template #default="{ row }">{{
                formatPercent(row.dividend_yield)
              }}</template>
            </el-table-column>
            <el-table-column label="年末价格" min-width="180">
              <template #default="{ row }">{{
                row.close_price > 0
                  ? formatMoney(row.close_price, detail.currency)
                  : "—"
              }}</template>
            </el-table-column>
          </el-table>
        </section>

        <el-empty
          v-if="!recentDividends.length && !recentQuarterlyPrices.length"
          description="暂无股息数据"
        />
      </template>
    </div>
  </el-dialog>
</template>
