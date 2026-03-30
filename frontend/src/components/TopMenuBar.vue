<script setup lang="ts">
defineProps<{
  activeView: "active" | "sold";
  activeCount: number;
  soldCount: number;
}>();

const emit = defineEmits<{
  (event: "change-view", value: "active" | "sold"): void;
}>();
</script>

<template>
  <nav class="top-menu">
    <div class="top-menu__brand">
      <span class="top-menu__eyebrow">Yield Ledger</span>
      <strong>息流账本</strong>
    </div>

    <div class="top-menu__nav">
      <button
        :class="['top-menu__link', { 'is-active': activeView === 'active' }]"
        type="button"
        @click="emit('change-view', 'active')"
      >
        <span>持仓总览</span>
        <span class="top-menu__count">{{ activeCount }}</span>
      </button>
      <button
        :class="['top-menu__link', { 'is-active': activeView === 'sold' }]"
        type="button"
        @click="emit('change-view', 'sold')"
      >
        <span>已卖出</span>
        <span class="top-menu__count">{{ soldCount }}</span>
      </button>
    </div>
  </nav>
</template>
