<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

import { searchStocks } from '../api/client'
import type { CreateStockPayload, StockSearchItem } from '../types'

const props = defineProps<{
  modelValue: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'submit', payload: CreateStockPayload): void
}>()

const formRef = ref<FormInstance>()
const lastAveragePrice = ref(1)
const searching = ref(false)
const selectedSecurity = ref<StockSearchItem | null>(null)
const clearedOnFocus = reactive({
  shares: false,
  average_price: false
})

type CreateHoldingForm = {
  security: string
  trade_date: string
  shares: number | null
  average_price: number | null
}

const form = reactive<CreateHoldingForm>({
  security: '',
  trade_date: new Date().toISOString().slice(0, 10),
  shares: 100,
  average_price: 1
})

function parseSecurityInput(value: string): { name: string; symbol: string } | null {
  // 兼容手输“名称（代码）”和从候选里点选两种路径。
  const raw = value.trim()
  if (!raw) return null

  const bracketMatch = raw.match(/^(.*?)\s*[（(]\s*([A-Za-z0-9.\-]+)\s*[）)]\s*$/)
  if (bracketMatch) {
    const name = bracketMatch[1]?.trim()
    const symbol = bracketMatch[2]?.trim().toUpperCase()
    if (name && symbol) return { name, symbol }
  }

  const tailMatch = raw.match(/^(.*?)[\s/]+([A-Za-z0-9.\-]+)$/)
  if (tailMatch) {
    const name = tailMatch[1]?.trim()
    const symbol = tailMatch[2]?.trim().toUpperCase()
    if (name && symbol) return { name, symbol }
  }

  return null
}

function formatSecurity(item: Pick<StockSearchItem, 'name' | 'normalized_symbol'>): string {
  return `${item.name}（${item.normalized_symbol}）`
}

const rules: FormRules<CreateHoldingForm> = {
  security: [
    { required: true, message: '请输入股票名称和代码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (selectedSecurity.value || parseSecurityInput(value)) {
          callback()
          return
        }
        callback(new Error('请输入“股票名称（代码）”格式'))
      },
      trigger: 'blur'
    }
  ],
  trade_date: [{ required: true, message: '请选择建仓日期', trigger: 'change' }],
  shares: [{ required: true, message: '请输入持仓数量', trigger: 'blur' }],
  average_price: [{ required: true, message: '请输入成本价', trigger: 'blur' }]
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      form.security = ''
      selectedSecurity.value = null
      form.trade_date = new Date().toISOString().slice(0, 10)
      form.shares = 100
      form.average_price = lastAveragePrice.value
      clearedOnFocus.shares = false
      clearedOnFocus.average_price = false
      nextTick(() => formRef.value?.clearValidate())
    }
  }
)

function clearNumberField(field: 'shares' | 'average_price') {
  if (clearedOnFocus[field]) return
  form[field] = null
  clearedOnFocus[field] = true
}

function handleSecurityInput(value: string) {
  if (!selectedSecurity.value) return
  if (value !== formatSecurity(selectedSecurity.value)) {
    selectedSecurity.value = null
  }
}

async function querySearch(query: string, callback: (items: Array<StockSearchItem & { value: string }>) => void) {
  // 候选列表只查本地缓存目录，不在输入阶段临时联网。
  const keyword = query.trim()
  if (!keyword) {
    callback([])
    return
  }

  searching.value = true
  try {
    const items = await searchStocks(keyword)
    callback(
      items.map((item) => ({
        ...item,
        value: formatSecurity(item),
      })),
    )
  } catch {
    callback([])
  } finally {
    searching.value = false
  }
}

function handleSelectSecurity(item: StockSearchItem) {
  selectedSecurity.value = item
  form.security = formatSecurity(item)
  void nextTick(() => formRef.value?.validateField('security'))
}

async function onSubmit() {
  // 提交前统一拆出名称和代码，后端接口仍保持简单。
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const parsed = selectedSecurity.value
    ? { name: selectedSecurity.value.name, symbol: selectedSecurity.value.normalized_symbol }
    : parseSecurityInput(form.security)
  if (!parsed) return
  lastAveragePrice.value = form.average_price || 1
  emit('submit', {
    name: parsed.name,
    symbol: parsed.symbol,
    trade_date: form.trade_date,
    shares: form.shares || 0,
    average_price: form.average_price || 0
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="添加持仓"
    width="560px"
    @close="emit('update:modelValue', false)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="股票名称（代码）" prop="security">
        <el-autocomplete
          v-model="form.security"
          :fetch-suggestions="querySearch"
          :trigger-on-focus="false"
          :debounce="180"
          :fit-input-width="true"
          placeholder="例如：招商银行 / 600036"
          clearable
          style="width: 100%"
          @input="handleSecurityInput"
          @select="handleSelectSecurity"
        >
          <template #default="{ item }">
            <div class="catalog-option">
              <div class="catalog-option__main">
                <strong>{{ item.name }}</strong>
                <span>{{ item.normalized_symbol }}</span>
              </div>
              <div class="catalog-option__meta">
                <span>{{ item.market === 'CN' ? 'A股' : item.market === 'HK' ? '港股' : '美股' }}</span>
                <span>{{ item.currency }}</span>
              </div>
            </div>
          </template>
          <template #suffix>
            <el-icon v-if="searching" class="is-loading">
              <Loading />
            </el-icon>
          </template>
        </el-autocomplete>
        <div class="field-hint">输入名称或代码，从本地缓存候选里点选即可。</div>
      </el-form-item>
      <el-form-item label="首次建仓日期" prop="trade_date">
        <el-date-picker v-model="form.trade_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="持仓数量" prop="shares">
        <el-input-number
          v-model="form.shares"
          :min="1"
          :step="100"
          :precision="0"
          style="width: 100%"
          @focus="clearNumberField('shares')"
        />
      </el-form-item>
      <el-form-item label="成本价" prop="average_price">
        <el-input-number
          v-model="form.average_price"
          :min="0.01"
          :precision="2"
          style="width: 100%"
          @focus="clearNumberField('average_price')"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSubmit">保存并同步</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.catalog-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.catalog-option__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.catalog-option__main strong {
  color: #23190d;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
}

.catalog-option__main span {
  color: #786a58;
  font-size: 12px;
  line-height: 1.2;
}

.catalog-option__meta {
  display: flex;
  gap: 8px;
  color: #9b8159;
  font-size: 12px;
  white-space: nowrap;
}

.field-hint {
  margin-top: 8px;
  color: #8e7c66;
  font-size: 12px;
  line-height: 1.4;
}
</style>
