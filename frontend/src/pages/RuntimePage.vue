<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { formatChinaTime, getRuntimeStatus } from '../api'

const loading = ref(false)
const runtime = ref({
  worker_count: 0,
  queue_size: 0,
  dropped_count: 0,
  throughput_per_second: 0,
  flush_count: 0,
  batch_size: 0,
  last_flush_size: 0,
  total_written: 0,
  last_flush_at: null,
  servers: [],
})

let timerId = null

function formatTimestamp(value) {
  return formatChinaTime(value)
}

function statusClass(status, enabled) {
  if (!enabled || status === '未启用' || status === '未配置Topic') {
    return 'muted'
  }
  if (status === '已连接') {
    return 'ok'
  }
  return 'warn'
}

async function loadRuntime(showError = true) {
  loading.value = true
  try {
    runtime.value = await getRuntimeStatus()
  } catch (error) {
    if (showError) {
      ElMessage.error(error.message)
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadRuntime()
  timerId = window.setInterval(() => loadRuntime(false), 5000)
})

onBeforeUnmount(() => {
  if (timerId) {
    window.clearInterval(timerId)
  }
})
</script>

<template>
  <div class="page-stack">
    <section class="runtime-grid" v-loading="loading">
      <div class="runtime-stat">
        <span>活动连接</span>
        <strong>{{ runtime.worker_count }}</strong>
        <em>已启动 MQTT 客户端数量</em>
      </div>
      <div class="runtime-stat">
        <span>队列积压</span>
        <strong>{{ runtime.queue_size }}</strong>
        <em>内存缓冲中等待入库的消息条数</em>
      </div>
      <div class="runtime-stat">
        <span>批量吞吐</span>
        <strong>{{ runtime.throughput_per_second }}</strong>
        <em>近 60 秒平均入库条数/秒</em>
      </div>
      <div class="runtime-stat">
        <span>丢弃消息</span>
        <strong>{{ runtime.dropped_count }}</strong>
        <em>队列满载时的累计丢弃条数</em>
      </div>
    </section>

    <section class="runtime-layout">
      <div class="content-card" v-loading="loading">
        <div class="card-header">
          <div>
            <h3>连接状态</h3>
            <p>逐台查看 MQTT 连接、重连次数与最近消息时间</p>
          </div>
        </div>
        <div class="runtime-list">
          <div v-for="server in runtime.servers" :key="server.server_id" class="runtime-server-card">
            <div class="runtime-server-header">
              <div>
                <strong>{{ server.server_name }}</strong>
                <span>{{ server.host }}:{{ server.port }}</span>
              </div>
              <span :class="['runtime-pill', statusClass(server.status, server.enabled)]">{{ server.status }}</span>
            </div>
            <div class="runtime-server-meta">
              <span>启用 Topic：{{ server.enabled_topic_count }}/{{ server.configured_topic_count }}</span>
              <span>重连次数：{{ server.reconnect_count }}</span>
              <span>心跳：{{ server.keepalive || '--' }}s</span>
            </div>
            <div class="runtime-server-meta">
              <span>建立连接：{{ formatTimestamp(server.connected_at) }}</span>
              <span>最近消息：{{ formatTimestamp(server.last_message_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="content-card" v-loading="loading">
        <div class="card-header">
          <div>
            <h3>写入通道</h3>
            <p>观察批量入库节奏，判断是否存在积压或写盘瓶颈</p>
          </div>
        </div>
        <ul class="runtime-side-list">
          <li>
            <span>批量大小</span>
            <strong>{{ runtime.batch_size }}</strong>
          </li>
          <li>
            <span>刷新间隔</span>
            <strong>{{ runtime.flush_interval_ms }} ms</strong>
          </li>
          <li>
            <span>累计刷新次数</span>
            <strong>{{ runtime.flush_count }}</strong>
          </li>
          <li>
            <span>最近一次批量</span>
            <strong>{{ runtime.last_flush_size }}</strong>
          </li>
          <li>
            <span>累计入库消息</span>
            <strong>{{ runtime.total_written }}</strong>
          </li>
          <li>
            <span>最近写入时间</span>
            <strong>{{ formatTimestamp(runtime.last_flush_at) }}</strong>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>