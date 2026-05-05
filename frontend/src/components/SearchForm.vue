<template>
  <section id="planner" class="planner-hero">
    <div class="hero-copy">
      <p class="eyebrow">Travel Agent</p>
      <h1>把一次旅行，打磨成一份漂亮的计划。</h1>
      <p class="hero-subtitle">
        输入目的地、时间和偏好，多智能体会并行完成景点、天气、酒店与预算分析。
      </p>

      <div class="hero-visual" aria-hidden="true">
        <div class="visual-toolbar">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div class="visual-map">
          <i class="pin pin-one"></i>
          <i class="pin pin-two"></i>
          <i class="pin pin-three"></i>
          <svg viewBox="0 0 360 180" role="presentation">
            <path d="M42 126 C92 26 132 150 190 76 C236 18 272 112 320 50" />
          </svg>
        </div>
        <div class="visual-metrics">
          <div>
            <strong>03</strong>
            <span>days</span>
          </div>
          <div>
            <strong>AI</strong>
            <span>plan</span>
          </div>
          <div>
            <strong>¥</strong>
            <span>budget</span>
          </div>
        </div>
      </div>
    </div>

    <div class="planner-form-shell">
      <div class="section-heading compact">
        <div>
          <p class="eyebrow">Start Here</p>
          <h2>创建行程</h2>
        </div>
        <a-tag color="default">FastAPI + Vue 3</a-tag>
      </div>

      <a-form layout="vertical" :model="form" @finish="$emit('submit')">
        <a-row :gutter="[16, 4]">
          <a-col :xs="24" :md="8">
            <a-form-item label="目的地城市" required>
              <a-input v-model:value="form.destination.city" placeholder="例如：杭州" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="区县 / 片区">
              <a-input v-model:value="form.destination.district" placeholder="例如：西湖区" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="出发城市">
              <a-input v-model:value="form.origin.city" placeholder="例如：上海" />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="8">
            <a-form-item label="开始日期" required>
              <a-date-picker
                v-model:value="form.start_date"
                value-format="YYYY-MM-DD"
                class="full-width"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="结束日期" required>
              <a-date-picker
                v-model:value="form.end_date"
                value-format="YYYY-MM-DD"
                class="full-width"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="人数" required>
              <a-input-number v-model:value="form.travelers" :min="1" :max="20" class="full-width" />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="8">
            <a-form-item label="预算等级">
              <a-segmented v-model:value="form.budget_level" :options="budgetOptions" block />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="行程节奏">
              <a-segmented v-model:value="form.pace" :options="paceOptions" block />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="8">
            <a-form-item label="住宿等级">
              <a-segmented v-model:value="form.hotel_level" :options="hotelOptions" block />
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-form-item label="兴趣标签">
              <a-select
                v-model:value="form.interests"
                mode="tags"
                :token-separators="[',', '，']"
                placeholder="城市地标、美食、博物馆"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item label="饮食偏好">
              <a-select
                v-model:value="form.dietary_preferences"
                mode="tags"
                :token-separators="[',', '，']"
                placeholder="清淡、素食、当地特色"
              />
            </a-form-item>
          </a-col>

          <a-col :span="24">
            <a-form-item label="补充要求">
              <a-textarea
                v-model:value="form.notes"
                :rows="3"
                placeholder="例如：带老人出行，希望少走路，晚上想看夜景"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <div class="toolbar-row">
          <a-button type="primary" html-type="submit" size="large" :loading="loading">
            <template #icon><SearchOutlined /></template>
            生成行程
          </a-button>
        </div>
      </a-form>
    </div>
  </section>
</template>

<script setup lang="ts">
import SearchOutlined from '@ant-design/icons-vue/SearchOutlined'

import type { TravelRequest } from '../types/travel'

defineProps<{
  form: TravelRequest
  loading: boolean
}>()

defineEmits<{
  submit: []
}>()

const budgetOptions = [
  { label: '经济', value: 'economy' },
  { label: '标准', value: 'standard' },
  { label: '高端', value: 'premium' }
]

const paceOptions = [
  { label: '轻松', value: 'relaxed' },
  { label: '均衡', value: 'balanced' },
  { label: '紧凑', value: 'packed' }
]

const hotelOptions = [
  { label: '实惠', value: 'budget' },
  { label: '舒适', value: 'comfort' },
  { label: '豪华', value: 'luxury' }
]
</script>

