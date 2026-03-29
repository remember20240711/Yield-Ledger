<script setup lang="ts">
import type { TransactionDetail } from '../types'
import { formatMoney, formatShares, formatTradePrice } from '../utils/format'

defineProps<{
  modelValue: boolean
  detail: TransactionDetail | null
  loading: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
</script>

<template>
  <!-- 这里保留原始交易流水，方便核对买卖记录和剩余成本。 -->
  <el-drawer
    :model-value="modelValue"
    title="持仓详情"
    size="min(720px, 100%)"
    @close="emit('update:modelValue', false)"
  >
    <div v-loading="loading">
      <template v-if="detail">
        <div class="drawer-head">
          <div>
            <div class="drawer-head__title">{{ detail.name }}</div>
            <div class="drawer-head__sub">{{ detail.symbol }}</div>
          </div>
          <el-tag type="info">{{ detail.currency }}</el-tag>
        </div>

        <div class="drawer-summary">
          <div>
            <span>累计总股数</span>
            <strong>{{ formatShares(detail.total_shares) }}</strong>
          </div>
          <div>
            <span>整体均价</span>
            <strong>{{ formatTradePrice(detail.average_cost, detail.currency) }}</strong>
          </div>
          <div>
            <span>累计总成本</span>
            <strong>{{ formatMoney(detail.total_cost, detail.currency) }}</strong>
          </div>
        </div>

        <el-table :data="detail.transactions" stripe>
          <el-table-column prop="trade_date" label="日期" min-width="120" />
          <el-table-column label="类型" min-width="100">
            <template #default="{ row }">
              <el-tag :type="row.transaction_type === 'buy' ? 'success' : 'warning'">
                {{ row.transaction_type === 'buy' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数量" min-width="140">
            <template #default="{ row }">{{ formatShares(row.shares) }}</template>
          </el-table-column>
          <el-table-column label="成交均价" min-width="160">
            <template #default="{ row }">{{ formatTradePrice(row.average_price, detail.currency) }}</template>
          </el-table-column>
          <el-table-column label="成交金额" min-width="160">
            <template #default="{ row }">{{ formatMoney(row.total_amount, detail.currency) }}</template>
          </el-table-column>
        </el-table>
      </template>
    </div>
  </el-drawer>
</template>
