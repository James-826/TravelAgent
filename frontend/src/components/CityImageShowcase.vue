<template>
  <section class="city-showcase" :style="accentStyle">
    <div v-if="image?.image_url" class="city-photo-wrap">
      <img class="city-photo" :src="image.image_url" :alt="image.alt_description || `${city} 城市图片`" />
      <div class="city-photo-overlay">
        <p class="eyebrow">City Preview</p>
        <h2>{{ city }}</h2>
        <p>{{ image.alt_description || '来自 Unsplash 的城市旅行图片' }}</p>
        <a v-if="image.photo_url" :href="image.photo_url" target="_blank" rel="noreferrer">
          查看 Unsplash 原图
        </a>
      </div>
    </div>

    <div v-else class="city-photo-empty">
      <p class="eyebrow">City Preview</p>
      <h2>{{ city || '目的地城市' }}</h2>
      <p>{{ emptyText }}</p>
    </div>

    <div class="city-credit">
      <span v-if="loading">正在加载城市图片</span>
      <span v-else-if="image?.photographer_name">
        Photo by
        <a :href="image.photographer_url || image.photo_url || '#'" target="_blank" rel="noreferrer">
          {{ image.photographer_name }}
        </a>
        on Unsplash
      </span>
      <span v-else>Unsplash API 城市图片展示</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { CityImage } from '../types/travel'

const props = defineProps<{
  city: string
  image: CityImage | null
  loading: boolean
}>()

const accentStyle = computed(() => ({
  '--city-accent': props.image?.color || '#111111'
}))

const emptyText = computed(() => {
  if (!props.image) {
    return '输入城市后将展示对应的旅行头图。'
  }
  if (!props.image.configured) {
    return '请在 backend/.env 中填写 UNSPLASH_ACCESS_KEY 后刷新页面。'
  }
  return props.image.alt_description || '暂未获取到城市图片。'
})
</script>

