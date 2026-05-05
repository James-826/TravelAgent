<template>
  <main class="app-shell">
    <SideAnchor :has-plan="Boolean(plan)" />

    <div class="content-shell">
      <SearchForm :form="form" :loading="loading" @submit="handleSubmit" />
      <CityImageShowcase :city="form.destination.city" :image="cityImage" :loading="imageLoading" />
      <ProgressPanel :loading="loading" :progress="progress" :agents="agents" />

      <div v-if="plan" id="trip-report" class="report-area">
        <DayTripEditor :plan="plan" />
        <BudgetSummary :budget="plan.budget" />
        <AmapPreview :plan="plan" />

        <section class="panel">
          <div class="section-heading compact">
            <div>
              <p class="eyebrow">Notes</p>
              <h2>假设与提醒</h2>
            </div>
          </div>
          <a-alert
            v-for="item in [...plan.assumptions, ...plan.warnings]"
            :key="item"
            type="info"
            show-icon
            :message="item"
          />
        </section>
      </div>

      <ExportToolbar
        v-if="plan"
        target-id="trip-report"
        :filename="`${plan.destination.city}-智能旅行计划`"
      />
    </div>
  </main>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { nextTick, onMounted, reactive, ref, watch } from 'vue'

import { createTripPlan, getCityImage } from '../api/travel'
import AmapPreview from '../components/AmapPreview.vue'
import BudgetSummary from '../components/BudgetSummary.vue'
import CityImageShowcase from '../components/CityImageShowcase.vue'
import DayTripEditor from '../components/DayTripEditor.vue'
import ExportToolbar from '../components/ExportToolbar.vue'
import ProgressPanel from '../components/ProgressPanel.vue'
import SearchForm from '../components/SearchForm.vue'
import SideAnchor from '../components/SideAnchor.vue'
import type { AgentReport, CityImage, TravelRequest, TripPlan } from '../types/travel'

const form = reactive<TravelRequest>({
  origin: { city: '上海' },
  destination: { city: '杭州', district: '西湖区' },
  start_date: offsetDate(7),
  end_date: offsetDate(9),
  travelers: 2,
  budget_level: 'standard',
  interests: ['城市地标', '美食', '博物馆'],
  pace: 'balanced',
  hotel_level: 'comfort',
  dietary_preferences: ['本地特色'],
  notes: ''
})

const loading = ref(false)
const progress = ref(0)
const plan = ref<TripPlan | null>(null)
const agents = ref<AgentReport[]>([])
const cityImage = ref<CityImage | null>(null)
const imageLoading = ref(false)
let progressTimer: number | undefined
let imageTimer: number | undefined

async function handleSubmit() {
  if (!form.destination.city || !form.start_date || !form.end_date) {
    message.warning('请填写目的地和日期')
    return
  }

  loading.value = true
  progress.value = 8
  agents.value = []
  startProgress()

  try {
    const response = await createTripPlan(JSON.parse(JSON.stringify(form)))
    plan.value = response.plan
    agents.value = response.agents
    progress.value = 100
    await nextTick()
    document.getElementById('plan')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (error) {
    message.error(error instanceof Error ? error.message : '行程生成失败')
  } finally {
    loading.value = false
    stopProgress()
  }
}

function startProgress() {
  stopProgress()
  progressTimer = window.setInterval(() => {
    if (progress.value < 92) {
      progress.value += progress.value < 45 ? 9 : 4
    }
  }, 450)
}

function stopProgress() {
  if (progressTimer) {
    window.clearInterval(progressTimer)
    progressTimer = undefined
  }
}

function offsetDate(days: number) {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

async function loadCityImage(city: string) {
  if (!city.trim()) {
    cityImage.value = null
    return
  }

  imageLoading.value = true
  try {
    cityImage.value = await getCityImage(city.trim())
  } catch {
    cityImage.value = {
      city,
      configured: false,
      alt_description: '城市图片加载失败，请确认后端服务和 Unsplash Key',
      source: 'fallback'
    }
  } finally {
    imageLoading.value = false
  }
}

onMounted(() => {
  void loadCityImage(form.destination.city)
})

watch(
  () => form.destination.city,
  (city) => {
    if (imageTimer) {
      window.clearTimeout(imageTimer)
    }
    imageTimer = window.setTimeout(() => {
      void loadCityImage(city)
    }, 500)
  }
)
</script>
