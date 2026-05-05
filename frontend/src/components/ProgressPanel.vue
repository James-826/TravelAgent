<template>
  <section id="progress" class="panel">
    <div class="section-heading compact">
      <div>
        <p class="eyebrow">Multi-agent Flow</p>
        <h2>并行执行进度</h2>
      </div>
      <a-progress type="circle" :percent="progress" :size="58" />
    </div>

    <a-steps :current="currentStep" :items="stepItems" />

    <a-timeline v-if="agents.length" class="agent-timeline">
      <a-timeline-item v-for="agent in agents" :key="agent.agent_name" :color="agent.status === 'success' ? 'green' : 'orange'">
        <strong>{{ agent.agent_name }}</strong>
        <p>{{ agent.summary }}</p>
        <a-alert
          v-for="warning in agent.warnings"
          :key="warning"
          type="warning"
          show-icon
          :message="warning"
        />
      </a-timeline-item>
    </a-timeline>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { AgentReport } from '../types/travel'

const props = defineProps<{
  loading: boolean
  progress: number
  agents: AgentReport[]
}>()

const currentStep = computed(() => {
  if (props.progress >= 100) {
    return 3
  }
  if (props.progress >= 70) {
    return 2
  }
  if (props.progress >= 35) {
    return 1
  }
  return props.loading ? 0 : -1
})

const stepItems = [
  { title: '景点 / 天气 / 酒店', description: '前三个 Agent 并行' },
  { title: '计划规划', description: '汇总结构化结果' },
  { title: '预算校准', description: '计算每日与总预算' },
  { title: '完成', description: '返回可编辑行程' }
]
</script>

