<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import type { CreateTransactionPayload, StockRow } from '../types'

const props = defineProps<{
  modelValue: boolean
  loading: boolean
  stock: StockRow | null
  mode: 'buy' | 'sell'
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'submit', payload: CreateTransactionPayload): void
}>()

const formRef = ref<FormInstance>()
const lastAveragePrice = ref(1)
const clearedOnFocus = reactive({
  shares: false,
  average_price: false
})

type TransactionForm = {
  transaction_type: 'buy' | 'sell'
  trade_date: string
  shares: number | null
  average_price: number | null
}

const form = reactive<TransactionForm>({
  transaction_type: 'buy',
  trade_date: new Date().toISOString().slice(0, 10),
  shares: 100,
  average_price: 1
})

const rules: FormRules<TransactionForm> = {
  trade_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  shares: [{ required: true, message: '请输入股数', trigger: 'blur' }],
  average_price: [{ required: true, message: '请输入价格', trigger: 'blur' }]
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      // 买入和卖出都优先带出当前缓存价，减少重复输入。
      form.transaction_type = props.mode
      form.trade_date = new Date().toISOString().slice(0, 10)
      form.shares = 100
      form.average_price = props.stock?.current_price || lastAveragePrice.value || 1
      clearedOnFocus.shares = false
      clearedOnFocus.average_price = false
    }
  }
)

function clearNumberField(field: 'shares' | 'average_price') {
  if (clearedOnFocus[field]) return
  form[field] = null
  clearedOnFocus[field] = true
}

async function onSubmit() {
  // 这里沿用后端的 average_price 字段名，但界面统一叫“价格”。
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  lastAveragePrice.value = form.average_price || 1
  emit('submit', {
    transaction_type: form.transaction_type,
    trade_date: form.trade_date,
    shares: form.shares || 0,
    average_price: form.average_price || 0
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="stock ? `${mode === 'buy' ? '买入' : '卖出'} · ${stock.name}` : mode === 'buy' ? '买入' : '卖出'"
    width="460px"
    @close="emit('update:modelValue', false)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item :label="mode === 'buy' ? '买入日期' : '卖出日期'" prop="trade_date">
        <el-date-picker v-model="form.trade_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item :label="mode === 'buy' ? '买入股数' : '卖出股数'" prop="shares">
        <el-input-number
          v-model="form.shares"
          :min="1"
          :step="100"
          :precision="0"
          style="width: 100%"
          @focus="clearNumberField('shares')"
        />
      </el-form-item>
      <el-form-item :label="mode === 'buy' ? '买入价格' : '卖出价格'" prop="average_price">
        <el-input-number
          v-model="form.average_price"
          :min="0.01"
          :precision="2"
          style="width: 100%"
          @focus="clearNumberField('average_price')"
        />
      </el-form-item>
      <div class="inline-tip">
        本次{{ mode === 'buy' ? '成交额' : '回收金额' }}：{{ ((form.shares || 0) * (form.average_price || 0)).toFixed(2) }}
      </div>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button :type="mode === 'buy' ? 'primary' : 'warning'" :loading="loading" @click="onSubmit">
        {{ mode === 'buy' ? '确认买入' : '确认卖出' }}
      </el-button>
    </template>
  </el-dialog>
</template>
