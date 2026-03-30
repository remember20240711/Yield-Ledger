<script setup lang="ts">
import { computed } from "vue";

import type { StockRow } from "../types";
import {
  formatDateTime,
  formatMoney,
  formatPercent,
  formatShares,
  formatTradePrice,
  marketLabel,
} from "../utils/format";

const props = defineProps<{
  stocks: StockRow[];
  loading: boolean;
  view: "active" | "sold";
}>();

const emit = defineEmits<{
  (event: "buy-stock", stock: StockRow): void;
  (event: "sell-stock", stock: StockRow): void;
  (event: "view-transactions", stock: StockRow): void;
  (event: "view-dividends", stock: StockRow): void;
  (event: "delete-stock", stock: StockRow): void;
}>();

const totalMarketValue = computed(() =>
  props.stocks.reduce((sum, stock) => sum + (stock.market_value || 0), 0),
);

function displayCurrentPrice(price: number, currency: string): string {
  // 没有缓存价时明确显示空值，避免误读成 0。
  return price > 0 ? formatTradePrice(price, currency) : "—";
}

function holdingWeight(stock: StockRow): string | null {
  if (totalMarketValue.value <= 0 || stock.market_value <= 0) return null;
  return formatPercent((stock.market_value / totalMarketValue.value) * 100);
}

function syncLabel(stock: StockRow): string {
  if (stock.sync_status === "pending") return "同步中";
  if (stock.sync_status === "error") return "同步异常";
  return formatDateTime(stock.last_synced_at);
}

function syncStateClass(stock: StockRow): string {
  if (stock.sync_status === "pending") return "pending";
  if (stock.sync_status === "error") return "error";
  return "ready";
}

function canSell(stock: StockRow): boolean {
  return stock.total_shares > 0;
}
</script>

<template>
  <section class="panel holdings-panel">
    <div class="panel__head panel__head--stack">
      <div class="panel__title">
        <span class="panel__kicker">Holdings</span>
        <h2>{{ props.view === "active" ? "股票持仓列表" : "已卖出归档" }}</h2>
      </div>

      <div class="panel__toolbar">
        <div class="panel__meta">
          <span class="holdings-count">{{ stocks.length }} 只股票</span>
        </div>
        <div class="panel__actions">
          <slot name="actions" />
        </div>
      </div>
    </div>

    <div v-if="!stocks.length && !loading" class="panel-empty">
      <div class="panel-empty__icon">+</div>
      <h3>{{ props.view === "active" ? "还没有持仓" : "还没有已卖出记录" }}</h3>
      <p>
        {{
          props.view === "active"
            ? "先添加第一只股票，系统会开始维护持仓数量、分红缓存和组合汇总。"
            : "卖出到 0 股的标的会自动出现在这里，方便单独查看历史。"
        }}
      </p>
    </div>

    <template v-else>
      <div class="holding-board holding-board--desktop" v-loading="loading">
        <div class="holding-board__head">
          <div>股票代码</div>
          <div>股票名称</div>
          <div>当前股息率</div>
          <div>预计每年分红</div>
          <div>当前持仓数量</div>
          <div>价格 / 成本价</div>
          <div>当前持仓市值</div>
          <div>盈亏</div>
          <div>操作</div>
        </div>

        <article v-for="stock in stocks" :key="stock.id" class="holding-row">
          <div class="holding-row__cell">
            <div class="holding-row__symbol">
              <strong>{{ stock.normalized_symbol }}</strong>
              <span
                :class="[
                  'market-badge',
                  `market-badge--${stock.market.toLowerCase()}`,
                ]"
              >
                {{ marketLabel(stock.market) }}
              </span>
            </div>
            <div class="holding-row__sync">
              <span
                :class="['sync-dot', `sync-dot--${syncStateClass(stock)}`]"
              />
              <span>{{ syncLabel(stock) }}</span>
            </div>
          </div>

          <div class="holding-row__cell">
            <div class="holding-row__name">{{ stock.name }}</div>
            <div v-if="holdingWeight(stock)" class="holding-row__submeta">
              <span class="weight-badge">仓位 {{ holdingWeight(stock) }}</span>
            </div>
          </div>

          <div class="holding-row__cell">
            <button
              type="button"
              class="yield-link"
              @click="emit('view-dividends', stock)"
            >
              {{ formatPercent(stock.current_dividend_yield) }}
            </button>
            <div
              v-if="stock.five_year_avg_yield > 0"
              class="holding-row__submeta"
            >
              <span class="yield-tag"
                >5Y {{ formatPercent(stock.five_year_avg_yield) }}</span
              >
            </div>
          </div>

          <div class="holding-row__cell holding-row__cell--number">
            {{ formatMoney(stock.annual_dividend, stock.base_currency) }}
          </div>

          <div class="holding-row__cell holding-row__cell--number">
            {{ formatShares(stock.total_shares) }}
          </div>

          <div class="holding-row__cell">
            <div class="holding-row__price">
              {{ displayCurrentPrice(stock.current_price, stock.currency) }}
            </div>
            <div class="holding-row__submeta">
              {{ formatTradePrice(stock.average_cost, stock.currency) }}
            </div>
          </div>

          <div class="holding-row__cell holding-row__cell--number">
            {{ formatMoney(stock.market_value, stock.base_currency) }}
          </div>

          <div
            class="holding-row__cell holding-row__cell--number"
            :class="stock.profit_loss >= 0 ? 'profit' : 'loss'"
          >
            {{ formatMoney(stock.profit_loss, stock.base_currency) }}
          </div>

          <div class="holding-row__cell">
            <div class="holding-row__actions">
              <div class="holding-row__action-line">
                <button
                  type="button"
                  class="card-action card-action--primary card-action--compact"
                  @click="emit('buy-stock', stock)"
                >
                  买入
                </button>
                <button
                  v-if="canSell(stock)"
                  type="button"
                  class="card-action card-action--secondary card-action--compact"
                  @click="emit('sell-stock', stock)"
                >
                  卖出
                </button>
              </div>

              <div
                class="holding-row__action-line holding-row__action-line--text"
              >
                <button
                  type="button"
                  class="text-action"
                  @click="emit('view-transactions', stock)"
                >
                  持仓详情
                </button>
                <button
                  type="button"
                  class="text-action text-action--danger"
                  @click="emit('delete-stock', stock)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </article>
      </div>

      <div class="holding-list holding-list--mobile" v-loading="loading">
        <article v-for="stock in stocks" :key="stock.id" class="holding-card">
          <div class="holding-card__top">
            <div class="holding-card__identity">
              <div class="holding-card__symbol-line">
                <strong>{{ stock.normalized_symbol }}</strong>
                <span
                  :class="[
                    'market-badge',
                    `market-badge--${stock.market.toLowerCase()}`,
                  ]"
                >
                  {{ marketLabel(stock.market) }}
                </span>
                <span v-if="holdingWeight(stock)" class="weight-badge">
                  {{ holdingWeight(stock) }}
                </span>
              </div>

              <div class="holding-card__name">{{ stock.name }}</div>

              <div class="holding-card__sync">
                <span
                  :class="['sync-dot', `sync-dot--${syncStateClass(stock)}`]"
                />
                <span>{{ syncLabel(stock) }}</span>
              </div>
            </div>

            <div class="holding-card__price-block">
              <span>当前股价</span>
              <strong>{{
                displayCurrentPrice(stock.current_price, stock.currency)
              }}</strong>
              <em :class="stock.profit_loss >= 0 ? 'profit' : 'loss'">
                {{ formatMoney(stock.profit_loss, stock.base_currency) }}
              </em>
            </div>
          </div>

          <div class="holding-card__metrics">
            <div class="metric-card">
              <span class="metric-card__label">当前股息率</span>
              <div class="metric-card__value">
                <button
                  type="button"
                  class="yield-link"
                  @click="emit('view-dividends', stock)"
                >
                  {{ formatPercent(stock.current_dividend_yield) }}
                </button>
                <span v-if="stock.five_year_avg_yield > 0" class="yield-tag">
                  5Y {{ formatPercent(stock.five_year_avg_yield) }}
                </span>
              </div>
            </div>

            <div class="metric-card">
              <span class="metric-card__label">年预计分红</span>
              <strong class="metric-card__value-text">
                {{ formatMoney(stock.annual_dividend, stock.base_currency) }}
              </strong>
            </div>

            <div class="metric-card">
              <span class="metric-card__label">当前持仓数量</span>
              <strong class="metric-card__value-text">{{
                formatShares(stock.total_shares)
              }}</strong>
            </div>

            <div class="metric-card">
              <span class="metric-card__label">当前持仓市值</span>
              <strong class="metric-card__value-text">
                {{ formatMoney(stock.market_value, stock.base_currency) }}
              </strong>
            </div>
          </div>

          <div class="holding-card__footer">
            <div class="holding-card__cost">
              <span
                >成本价
                {{ formatTradePrice(stock.average_cost, stock.currency) }}</span
              >
              <span
                >总成本
                {{ formatMoney(stock.total_cost, stock.base_currency) }}</span
              >
            </div>

            <div class="holding-card__actions">
              <div class="holding-card__action-group">
                <button
                  type="button"
                  class="card-action card-action--primary"
                  @click="emit('buy-stock', stock)"
                >
                  买入
                </button>
                <button
                  v-if="canSell(stock)"
                  type="button"
                  class="card-action card-action--secondary"
                  @click="emit('sell-stock', stock)"
                >
                  卖出
                </button>
              </div>

              <div
                class="holding-card__action-group holding-card__action-group--text"
              >
                <button
                  type="button"
                  class="text-action"
                  @click="emit('view-transactions', stock)"
                >
                  持仓详情
                </button>
                <button
                  type="button"
                  class="text-action text-action--danger"
                  @click="emit('delete-stock', stock)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>
