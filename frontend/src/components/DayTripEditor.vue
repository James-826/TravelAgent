<template>
  <section id="plan" class="panel">
    <div class="section-heading compact">
      <div>
        <p class="eyebrow">Editable Plan</p>
        <h2>{{ plan.title }}</h2>
      </div>
      <a-switch v-model:checked="editing" checked-children="编辑" un-checked-children="预览" />
    </div>

    <a-collapse v-model:activeKey="activeKeys" class="day-collapse">
      <a-collapse-panel v-for="day in plan.days" :key="String(day.day_index)">
        <template #header>
          <div class="day-header">
            <strong>Day {{ day.day_index }}</strong>
            <span>{{ day.theme }}</span>
            <a-tag v-if="day.weather" color="blue">{{ day.weather.condition }}</a-tag>
          </div>
        </template>

        <div class="day-body">
          <a-row :gutter="[16, 16]">
            <a-col :xs="24" :lg="14">
              <a-form layout="vertical">
                <a-form-item label="主题">
                  <a-input v-if="editing" v-model:value="day.theme" />
                  <p v-else class="readonly-text">{{ day.theme }}</p>
                </a-form-item>
                <a-form-item label="概览">
                  <a-textarea v-if="editing" v-model:value="day.summary" :rows="3" />
                  <p v-else class="readonly-text">{{ day.summary }}</p>
                </a-form-item>
              </a-form>

              <div class="subsection-title">景点</div>
              <div class="item-list">
                <div v-for="attraction in day.attractions" :key="attraction.id" class="list-row">
                  <div>
                    <strong>{{ attraction.name }}</strong>
                    <p>{{ attraction.category }} · {{ attraction.location.label || attraction.location.address || attraction.location.city }}</p>
                    <a-space wrap>
                      <a-tag v-for="tag in attraction.tags" :key="tag">{{ tag }}</a-tag>
                    </a-space>
                  </div>
                  <div class="row-actions">
                    <a-input-number
                      v-if="editing"
                      v-model:value="attraction.duration_hours"
                      :min="0.5"
                      :max="12"
                      :step="0.5"
                      addon-after="h"
                    />
                    <span v-else>{{ attraction.duration_hours }}h</span>
                  </div>
                </div>
              </div>
            </a-col>

            <a-col :xs="24" :lg="10">
              <div class="info-stack">
                <div class="info-box">
                  <span>预计花费</span>
                  <strong>{{ formatMoney(day.estimated_cost, plan.budget.currency) }}</strong>
                </div>
                <div class="info-box" v-if="day.hotel">
                  <span>住宿</span>
                  <strong>{{ day.hotel.name }}</strong>
                  <p>{{ day.hotel.location.district || day.hotel.location.city }}</p>
                </div>
                <div class="info-box" v-if="day.weather">
                  <span>天气</span>
                  <strong>{{ day.weather.temperature_low }}°C - {{ day.weather.temperature_high }}°C</strong>
                  <p>{{ day.weather.tips.join(' / ') }}</p>
                </div>
              </div>

              <div class="subsection-title">餐饮</div>
              <div class="meal-list">
                <div v-for="meal in day.meals" :key="meal.id" class="meal-row">
                  <span>{{ mealTypeText[meal.meal_type] }}</span>
                  <strong>{{ meal.name }}</strong>
                  <em>{{ formatMoney(meal.price_per_person, plan.budget.currency) }}/人</em>
                </div>
              </div>

              <div class="subsection-title">交通与备注</div>
              <a-list size="small" :data-source="[...day.transportation, ...day.notes]">
                <template #renderItem="{ item }">
                  <a-list-item>{{ item }}</a-list-item>
                </template>
              </a-list>
            </a-col>
          </a-row>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import type { TripPlan } from '../types/travel'
import { formatMoney } from '../utils/money'

const props = defineProps<{
  plan: TripPlan
}>()

const editing = ref(false)
const activeKeys = ref(props.plan.days.map((day) => String(day.day_index)))

const mealTypeText = {
  breakfast: '早餐',
  lunch: '午餐',
  dinner: '晚餐',
  snack: '加餐'
}
</script>

