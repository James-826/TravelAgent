<template>
  <section id="export" class="panel export-panel">
    <div class="section-heading compact">
      <div>
        <p class="eyebrow">Export</p>
        <h2>导出行程</h2>
      </div>
      <a-space wrap>
        <a-button :loading="exporting" @click="capturePng">
          <template #icon><PictureOutlined /></template>
          PNG
        </a-button>
        <a-button type="primary" :loading="exporting" @click="exportPdf">
          <template #icon><FilePdfOutlined /></template>
          PDF
        </a-button>
      </a-space>
    </div>
  </section>
</template>

<script setup lang="ts">
import FilePdfOutlined from '@ant-design/icons-vue/FilePdfOutlined'
import PictureOutlined from '@ant-design/icons-vue/PictureOutlined'
import { message } from 'ant-design-vue'
import { ref } from 'vue'

const props = defineProps<{
  targetId: string
  filename: string
}>()

const exporting = ref(false)

async function getCanvas() {
  const target = document.getElementById(props.targetId)
  if (!target) {
    throw new Error('未找到导出区域')
  }
  const { default: html2canvas } = await import('html2canvas')
  return html2canvas(target, {
    scale: 2,
    backgroundColor: '#ffffff',
    useCORS: true
  })
}

async function capturePng() {
  exporting.value = true
  try {
    const canvas = await getCanvas()
    const link = document.createElement('a')
    link.href = canvas.toDataURL('image/png')
    link.download = `${props.filename}.png`
    link.click()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

async function exportPdf() {
  exporting.value = true
  try {
    const canvas = await getCanvas()
    const { default: jsPDF } = await import('jspdf')
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pageWidth = 210
    const pageHeight = 297
    const imgHeight = (canvas.height * pageWidth) / canvas.width
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, pageWidth, imgHeight)
    heightLeft -= pageHeight

    while (heightLeft > 0) {
      position -= pageHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, pageWidth, imgHeight)
      heightLeft -= pageHeight
    }

    pdf.save(`${props.filename}.pdf`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exporting.value = false
  }
}
</script>
