<template>
  <section id="budget" class="panel">
    <div class="section-heading compact">
      <div>
        <p class="eyebrow">Budget</p>
        <h2>预算计算</h2>
      </div>
      <a-statistic title="总预算" :value="total" prefix="¥" />
    </div>

    <div class="budget-grid">
      <div v-for="item in items" :key="item.label" class="budget-item">
        <span>{{ item.label }}</span>
        <strong>{{ formatMoney(item.value, budget.currency) }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { BudgetBreakdown } from '../types/travel'
import { formatMoney, toNumber } from '../utils/money'

const props = defineProps<{
  budget: BudgetBreakdown
}>()

const total = computed(() => toNumber(props.budget.grand_total))

const items = computed(() => [
  { label: '景点门票', value: props.budget.attraction_total },
  { label: '住宿', value: props.budget.hotel_total },
  { label: '餐饮', value: props.budget.meal_total },
  { label: '交通', value: props.budget.transport_total },
  { label: '弹性预留', value: props.budget.buffer_total }
])
</script>

