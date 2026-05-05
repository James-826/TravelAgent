<template>
  <nav class="side-anchor" aria-label="页面导航">
    <a href="#planner">查询</a>
    <a href="#progress">进度</a>
    <a href="#plan" :class="{ disabled: !hasPlan }">行程</a>
    <a href="#budget" :class="{ disabled: !hasPlan }">预算</a>
    <a href="#map" :class="{ disabled: !hasPlan }">地图</a>
    <a href="#export" :class="{ disabled: !hasPlan }">导出</a>
  </nav>
</template>

<script setup lang="ts">
defineProps<{
  hasPlan: boolean
}>()
</script>

