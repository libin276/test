<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeviceRank, getMessageTrend, getTopicRank } from '../api'

const trendData = ref([])
const topicRank = ref([])
const deviceRank = ref([])
const loading = ref(false)

function calcWidth(value, max) {
  return `${Math.round((value / max) * 100)}%`
}

async function loadStats() {
  loading.value = true
  try {
    const [trend, topics, devices] = await Promise.all([
      getMessageTrend(),
      getTopicRank(),
      getDeviceRank(),
    ])
    trendData.value = trend
    topicRank.value = topics
    deviceRank.value = devices
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <div class="page-stack">
    <section class="content-card" v-loading="loading">
      <div class="card-header">
        <div>
          <h3>消息量趋势</h3>
          <p>按小时查看采集消息波动，用于判断峰值和异常抖动</p>
        </div>
      </div>
      <div class="trend-grid">
        <div v-for="item in trendData" :key="item.label" class="trend-item">
          <div class="trend-bar-wrap">
            <div class="trend-bar" :style="{ height: `${item.value}px` }"></div>
          </div>
          <strong>{{ item.value }}</strong>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </section>

    <section class="rank-grid">
      <div class="content-card">
        <div class="card-header">
          <div>
            <h3>活跃 Topic 排行</h3>
            <p>高频 Topic 用于定位异常风暴和热点链路</p>
          </div>
        </div>
        <div class="rank-list">
          <div v-for="item in topicRank" :key="item.name" class="rank-item">
            <div>
              <strong>{{ item.name }}</strong>
              <span>{{ item.count }} 条</span>
            </div>
            <div class="rank-bar">
              <div class="rank-fill blue" :style="{ width: calcWidth(item.count, topicRank[0]?.count || item.count || 1) }"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="content-card">
        <div class="card-header">
          <div>
            <h3>设备活跃度排行</h3>
            <p>快速查看异常活跃设备，辅助设备侧排障</p>
          </div>
        </div>
        <div class="rank-list">
          <div v-for="item in deviceRank" :key="item.name" class="rank-item">
            <div>
              <strong>{{ item.name }}</strong>
              <span>{{ item.count }} 条</span>
            </div>
            <div class="rank-bar">
              <div class="rank-fill green" :style="{ width: calcWidth(item.count, deviceRank[0]?.count || item.count || 1) }"></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
