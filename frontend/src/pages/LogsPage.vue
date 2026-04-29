<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { buildExportUrl, cleanupMessages, formatChinaTime, getMessages, getServers, getTopics } from '../api'

const loading = ref(false)
const data = ref([])
const serverOptions = ref([])
const topicOptions = ref([])
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0,
})
const summary = reactive({
  total: 0,
  uplink: 0,
  downlink: 0,
})
const filters = reactive({
  server: '',
  topics: [],
  direction: '',
  dateRange: [],
  keyword: '',
})
const detailVisible = ref(false)
const activeMessage = ref(null)
const cleanupVisible = ref(false)
const cleanupSubmitting = ref(false)
const cleanupForm = reactive({
  server_id: '',
  before: '',
})

const dialogDirectionClass = computed(() => {
  if (!activeMessage.value) {
    return 'up'
  }
  return activeMessage.value.direction === '上行' ? 'up' : 'down'
})

function buildQuery() {
  return {
    server_id: filters.server || undefined,
    topics: filters.topics,
    keyword: filters.keyword,
    direction: filters.direction || undefined,
    start: filters.dateRange?.[0] ? new Date(filters.dateRange[0]).toISOString() : undefined,
    end: filters.dateRange?.[1] ? new Date(filters.dateRange[1]).toISOString() : undefined,
    page: pagination.page,
    size: pagination.size,
  }
}

async function loadBaseOptions() {
  try {
    const [servers, topics] = await Promise.all([getServers(), getTopics()])
    serverOptions.value = servers
    topicOptions.value = topics
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function loadMessages() {
  loading.value = true
  try {
    const response = await getMessages(buildQuery())
    data.value = response.items
    pagination.total = response.total
    summary.total = response.summary.total
    summary.uplink = response.summary.uplink
    summary.downlink = response.summary.downlink
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadMessages()
}

function handleReset() {
  filters.server = ''
  filters.topics = []
  filters.direction = ''
  filters.dateRange = []
  filters.keyword = ''
  pagination.page = 1
  loadMessages()
}

function handlePageChange(page) {
  pagination.page = page
  loadMessages()
}

function handleSizeChange(size) {
  pagination.size = size
  pagination.page = 1
  loadMessages()
}

function handleExport() {
  window.open(buildExportUrl(buildQuery()), '_blank')
}

function formatTimestamp(value) {
  return formatChinaTime(value)
}

function openCleanupDialog() {
  cleanupForm.server_id = filters.server || ''
  cleanupForm.before = ''
  cleanupVisible.value = true
}

async function submitCleanup() {
  if (!cleanupForm.before) {
    ElMessage.error('请选择清理截止时间')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认清理 ${formatTimestamp(cleanupForm.before)} 之前的日志吗？该操作不可恢复。`,
      '清理确认',
      { type: 'warning' },
    )
  } catch {
    return
  }

  cleanupSubmitting.value = true
  try {
    const response = await cleanupMessages({
      server_id: cleanupForm.server_id || null,
      before: new Date(cleanupForm.before).toISOString(),
    })
    ElMessage.success(`已清理 ${response.deleted} 条日志`)
    cleanupVisible.value = false
    pagination.page = 1
    await loadMessages()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    cleanupSubmitting.value = false
  }
}

function showDetail(message) {
  activeMessage.value = message
  detailVisible.value = true
}

async function copyPayload(payload) {
  try {
    await navigator.clipboard.writeText(payload)
    ElMessage.success('消息内容已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

onMounted(async () => {
  await loadBaseOptions()
  await loadMessages()
})
</script>

<template>
  <div class="page-stack">
    <section class="metrics-row">
      <div class="stat-card large">
        <span>今日日志总量</span>
        <strong>{{ summary.total }}</strong>
        <em>较昨日 +12%</em>
      </div>
      <div class="stat-card large success">
        <span>上行消息</span>
        <strong>{{ summary.uplink }}</strong>
        <em>设备/网关 -> 云平台</em>
      </div>
      <div class="stat-card large warning">
        <span>下行消息</span>
        <strong>{{ summary.downlink }}</strong>
        <em>云平台 -> 网关/设备</em>
      </div>
    </section>

    <section class="toolbar-card">
      <div class="toolbar-grid logs-toolbar">
        <el-select v-model="filters.server" placeholder="服务器" clearable>
          <el-option
            v-for="item in serverOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
        <el-select v-model="filters.topics" multiple collapse-tags placeholder="Topic">
          <el-option
            v-for="item in topicOptions"
            :key="item.id"
            :label="item.topic"
            :value="item.topic"
          />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="消息体关键字" clearable />
        <el-select v-model="filters.direction" placeholder="消息方向" clearable>
          <el-option label="上行" value="上行" />
          <el-option label="下行" value="下行" />
        </el-select>
        <el-date-picker
          v-model="filters.dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
        />
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="success" plain @click="handleExport">导出结果</el-button>
        <el-button type="danger" plain @click="openCleanupDialog">清理历史日志</el-button>
      </div>
    </section>

    <section class="content-card">
      <div class="card-header split-header">
        <div>
          <h3>消息日志</h3>
          <p>方向字段采用显著颜色标记，便于快速区分上下行链路</p>
        </div>
      </div>
      <el-table v-loading="loading" :data="data" stripe>
        <el-table-column label="时间戳" width="182">
          <template #default="scope">
            {{ formatTimestamp(scope.row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="server_name" label="服务器" width="150" />
        <el-table-column prop="topic" label="Topic" min-width="220" show-overflow-tooltip />
        <el-table-column label="方向" width="100">
          <template #default="scope">
            <span :class="['direction-badge', scope.row.direction === '上行' ? 'up' : 'down']">
              {{ scope.row.direction }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="qos" label="QoS" width="80" />
        <el-table-column prop="device_id" label="设备ID" width="120" />
        <el-table-column prop="payload" label="消息内容" min-width="320" show-overflow-tooltip />
        <el-table-column label="操作" fixed="right" width="160">
          <template #default="scope">
            <el-button link type="primary" @click="showDetail(scope.row)">详情</el-button>
            <el-button link type="primary" @click="copyPayload(scope.row.payload)">复制</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <span>共 {{ pagination.total }} 条</span>
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.size"
          :total="pagination.total"
          layout="sizes, prev, pager, next"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>

    <el-dialog v-model="detailVisible" title="消息详情" width="760px">
      <template v-if="activeMessage">
        <div class="detail-grid">
          <div class="detail-item">
            <span>时间戳</span>
            <strong>{{ formatTimestamp(activeMessage.timestamp) }}</strong>
          </div>
          <div class="detail-item">
            <span>服务器</span>
            <strong>{{ activeMessage.server_name }}</strong>
          </div>
          <div class="detail-item">
            <span>Topic</span>
            <strong>{{ activeMessage.topic }}</strong>
          </div>
          <div class="detail-item">
            <span>方向</span>
            <strong :class="['direction-badge', dialogDirectionClass]">{{ activeMessage.direction }}</strong>
          </div>
          <div class="detail-item">
            <span>QoS</span>
            <strong>{{ activeMessage.qos }}</strong>
          </div>
          <div class="detail-item">
            <span>设备ID</span>
            <strong>{{ activeMessage.device_id || '--' }}</strong>
          </div>
        </div>
        <div class="payload-block raw-block">
          <div class="payload-header">
            <h4>原始报文</h4>
            <el-button link type="primary" @click="copyPayload(activeMessage.raw || activeMessage.payload)">复制原始报文</el-button>
          </div>
          <pre>{{ activeMessage.raw || activeMessage.payload }}</pre>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="cleanupVisible" title="清理消息日志" width="520px">
      <el-form label-width="110px">
        <el-form-item label="服务器范围">
          <el-select v-model="cleanupForm.server_id" placeholder="全部服务器" clearable>
            <el-option
              v-for="item in serverOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="清理截止时间">
          <el-date-picker
            v-model="cleanupForm.before"
            type="datetime"
            placeholder="请选择北京时间"
          />
        </el-form-item>
        <el-alert
          title="将删除所选时间点之前的消息日志，请先确认是否已完成导出。"
          type="warning"
          :closable="false"
          show-icon
        />
      </el-form>
      <template #footer>
        <el-button @click="cleanupVisible = false">取消</el-button>
        <el-button type="danger" :loading="cleanupSubmitting" @click="submitCleanup">确认清理</el-button>
      </template>
    </el-dialog>
  </div>
</template>
