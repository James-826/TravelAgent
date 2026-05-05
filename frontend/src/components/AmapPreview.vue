<template>
  <section id="map" class="panel">
    <div class="section-heading compact">
      <div>
        <p class="eyebrow">AMap</p>
        <h2>高德地图预览</h2>
      </div>
      <a-tag :color="mapReady ? 'success' : statusColor">{{ statusText }}</a-tag>
    </div>

    <div ref="mapElement" class="map-canvas">
      <div v-if="!canRenderMap" class="map-empty">
        <EnvironmentOutlined />
        <h3>{{ emptyTitle }}</h3>
        <p>{{ emptyDescription }}</p>
        <div class="map-config-list">
          <span :class="{ ready: hasWebKey }">VITE_AMAP_KEY</span>
          <span :class="{ ready: hasSecurityCode }">VITE_AMAP_SECURITY_JS_CODE</span>
          <span :class="{ ready: hasGeoPoints }">route_points 经纬度：{{ points.length }} 个</span>
        </div>
      </div>
    </div>

    <div class="route-strip">
      <div v-for="point in visiblePoints" :key="point.label" class="route-point">
        <span></span>
        <strong>{{ point.label }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import EnvironmentOutlined from '@ant-design/icons-vue/EnvironmentOutlined'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import type { Location, TripPlan } from '../types/travel'

const props = defineProps<{
  plan: TripPlan
}>()

type GeoPoint = Location & { latitude: number; longitude: number }

const mapElement = ref<HTMLElement | null>(null)
const mapReady = ref(false)
let mapInstance: any = null

const points = computed<GeoPoint[]>(() =>
  dedupeLocations(props.plan.days.flatMap((day) => day.route_points).filter(hasCoordinates))
)

const hasWebKey = computed(() => Boolean(import.meta.env.VITE_AMAP_KEY))
const hasSecurityCode = computed(() => Boolean(import.meta.env.VITE_AMAP_SECURITY_JS_CODE))
const hasGeoPoints = computed(() => points.value.length > 0)

const visiblePoints = computed(() =>
  dedupeLocations(props.plan.days.flatMap((day) => day.route_points))
    .slice(0, 12)
    .map((point) => ({ label: point.label || point.address || point.district || point.city }))
)

const canRenderMap = computed(() => hasWebKey.value && hasGeoPoints.value)

const statusText = computed(() => {
  if (mapReady.value) {
    return '已加载'
  }
  if (!hasWebKey.value) {
    return '缺少 Web Key'
  }
  if (!hasGeoPoints.value) {
    return '等待坐标'
  }
  return '可加载'
})

const statusColor = computed(() => {
  if (!hasWebKey.value) {
    return 'warning'
  }
  if (!hasGeoPoints.value) {
    return 'default'
  }
  return 'processing'
})

const emptyTitle = computed(() => {
  if (!hasWebKey.value) {
    return '需要高德 Web端(JS API) Key'
  }
  if (!hasGeoPoints.value) {
    return '等待高德 MCP 返回经纬度'
  }
  return '地图即将加载'
})

const emptyDescription = computed(() => {
  if (!hasWebKey.value) {
    return '请在 frontend/.env 填写 VITE_AMAP_KEY；如果使用 JS API 2.0 安全密钥，也填写 VITE_AMAP_SECURITY_JS_CODE。'
  }
  if (!hasGeoPoints.value) {
    return '后端会通过高德 MCP 和 POI 详情接口补全路线点位坐标。'
  }
  return '正在加载高德地图组件。'
})

async function renderMap() {
  if (!canRenderMap.value || !mapElement.value) {
    return
  }

  const securityJsCode = import.meta.env.VITE_AMAP_SECURITY_JS_CODE
  if (securityJsCode) {
    window._AMapSecurityConfig = { securityJsCode }
  }

  const { default: AMapLoader } = await import('@amap/amap-jsapi-loader')
  const AMap = await AMapLoader.load({
    key: import.meta.env.VITE_AMAP_KEY,
    version: '2.0',
    plugins: ['AMap.Marker', 'AMap.Polyline']
  })

  await nextTick()
  const first = points.value[0]
  mapInstance?.destroy?.()
  mapInstance = new AMap.Map(mapElement.value, {
    zoom: 12,
    center: [first.longitude, first.latitude],
    viewMode: '2D'
  })

  const path: [number, number][] = points.value.map((point) => [point.longitude, point.latitude])
  path.forEach((position: [number, number], index: number) => {
    new AMap.Marker({
      map: mapInstance,
      position,
      label: { content: String(index + 1), direction: 'top' }
    })
  })
  new AMap.Polyline({
    map: mapInstance,
    path,
    strokeColor: '#1677ff',
    strokeWeight: 5,
    strokeOpacity: 0.85
  })
  mapReady.value = true
}

onMounted(renderMap)
watch(() => props.plan.id, renderMap)

function hasCoordinates(point: Location): point is GeoPoint {
  return typeof point.latitude === 'number' && typeof point.longitude === 'number'
}

function dedupeLocations<T extends Location>(locations: T[]): T[] {
  const seen = new Set<string>()
  const result: T[] = []
  for (const location of locations) {
    const key =
      typeof location.latitude === 'number' && typeof location.longitude === 'number'
        ? `${location.longitude.toFixed(6)},${location.latitude.toFixed(6)}`
        : location.amap_poi_id || location.label || `${location.city}-${location.address}`
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    result.push(location)
  }
  return result
}
</script>
