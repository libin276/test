<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatChinaTime } from '../api'
import {
  createServer,
  deleteServer,
  getServers,
  toggleServer,
  updateServer,
} from '../api'

const loading = ref(false)
const submitting = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const formRef = ref(null)
const editingId = ref(null)
const activeServer = ref(null)

const filters = reactive({
  keyword: '',
  status: '',
})

const form = reactive({
  name: '',
  host: '',
  port: 1883,
  username: '',
  password: '',
  tls: false,
  enabled: true,
  remark: '',
})

const rules = {
  name: [{ required: true, message: '请输入服务器名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入服务器地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'change' }],
}

const totalServers = computed(() => tableData.value.length)
const onlineServers = computed(() => tableData.value.filter((item) => item.status === '已连接').length)
const dialogTitle = computed(() => (editingId.value ? '编辑服务器' : '新增服务器'))

function resetForm() {
  Object.assign(form, {
    name: '',
    host: '',
    port: 1883,
    username: '',
    password: '',
    tls: false,
    enabled: true,
    remark: '',
  })
  editingId.value = null
}

async function loadServers() {
  loading.value = true
  try {
    tableData.value = await getServers({
      keyword: filters.keyword,
      status: filters.status,
    })
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  loadServers()
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    host: row.host,
    port: row.port,
    username: row.username || '',
    password: row.password || '',
    tls: row.tls,
    enabled: row.enabled,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

function openDetailDialog(row) {
  activeServer.value = row
  detailVisible.value = true
}

function formatTimestamp(value) {
  return formatChinaTime(value)
}

async function submitForm() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      ...form,
      username: form.username || null,
      password: form.password || null,
      remark: form.remark || null,
    }
    if (editingId.value) {
      await updateServer(editingId.value, payload)
      ElMessage.success('服务器已更新')
    } else {
      await createServer(payload)
      ElMessage.success('服务器已创建')
    }
    dialogVisible.value = false
    resetForm()
    loadServers()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    submitting.value = false
  }
}

async function handleToggle(row, value) {
  try {
    const updated = await toggleServer(row.id, value)
    Object.assign(row, updated)
    ElMessage.success(value ? '服务器已启用' : '服务器已禁用')
  } catch (error) {
    row.enabled = !value
    ElMessage.error(error.message)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除服务器“${row.name}”吗？`, '删除确认', {
      type: 'warning',
    })
    await deleteServer(row.id)
    ElMessage.success('服务器已删除')
    loadServers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

onMounted(loadServers)
</script>

<template>
  <div class="page-stack">
    <section class="hero-panel">
      <div>
        <p class="hero-kicker">服务器接入</p>
        <h2>多 MQTT 服务器统一接入与状态管理</h2>
        <p class="hero-desc">集中维护连接配置、启用状态和接入健康度，支撑排障和日志采集。</p>
      </div>
      <div class="hero-stats">
        <div class="stat-card compact">
          <span>已接入服务器</span>
          <strong>{{ totalServers }}</strong>
        </div>
        <div class="stat-card compact accent">
          <span>在线连接</span>
          <strong>{{ onlineServers }}</strong>
        </div>
      </div>
    </section>

    <section class="toolbar-card">
      <div class="toolbar-grid">
        <el-input v-model="filters.keyword" placeholder="搜索服务器名称或地址" clearable />
        <el-select v-model="filters.status" placeholder="连接状态" clearable>
          <el-option label="连接中" value="连接中" />
          <el-option label="已连接" value="已连接" />
          <el-option label="重连中" value="重连中" />
          <el-option label="未配置Topic" value="未配置Topic" />
          <el-option label="未启用" value="未启用" />
        </el-select>
        <el-button type="primary" @click="loadServers">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" plain @click="openCreateDialog">新增服务器</el-button>
      </div>
    </section>

    <section class="content-card">
      <div class="card-header">
        <div>
          <h3>服务器列表</h3>
          <p>支持启用、禁用、编辑和删除操作</p>
        </div>
      </div>
      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column prop="name" label="服务器名称" min-width="180" />
        <el-table-column prop="host" label="地址" min-width="180" />
        <el-table-column prop="port" label="端口" width="90" />
        <el-table-column label="TLS" width="90">
          <template #default="scope">
            <el-tag :type="scope.row.tls ? 'success' : 'info'">{{ scope.row.tls ? '启用' : '关闭' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="topic_count" label="订阅数" width="90" />
        <el-table-column label="连接状态" width="110">
          <template #default="scope">
            <span :class="['status-dot', scope.row.status === '已连接' ? 'ok' : scope.row.status === '重连中' ? 'warn' : 'muted']"></span>
            {{ scope.row.status }}
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="是否启用" width="100">
          <template #default="scope">
            <el-switch
              :model-value="scope.row.enabled"
              inline-prompt
              active-text="开"
              inactive-text="关"
              @change="(value) => handleToggle(scope.row, value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="182">
          <template #default="scope">
            {{ formatTimestamp(scope.row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="220">
          <template #default="scope">
            <el-button link type="primary" @click="openDetailDialog(scope.row)">详情</el-button>
            <el-button link type="primary" @click="openEditDialog(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="detailVisible" title="服务器详情" width="680px">
      <template v-if="activeServer">
        <div class="detail-grid">
          <div class="detail-item">
            <span>服务器名称</span>
            <strong>{{ activeServer.name }}</strong>
          </div>
          <div class="detail-item">
            <span>连接状态</span>
            <strong>{{ activeServer.status }}</strong>
          </div>
          <div class="detail-item">
            <span>地址</span>
            <strong>{{ activeServer.host }}</strong>
          </div>
          <div class="detail-item">
            <span>端口</span>
            <strong>{{ activeServer.port }}</strong>
          </div>
          <div class="detail-item">
            <span>TLS</span>
            <strong>{{ activeServer.tls ? '启用' : '关闭' }}</strong>
          </div>
          <div class="detail-item">
            <span>订阅数</span>
            <strong>{{ activeServer.topic_count }}</strong>
          </div>
          <div class="detail-item">
            <span>用户名</span>
            <strong>{{ activeServer.username || '--' }}</strong>
          </div>
          <div class="detail-item">
            <span>更新时间</span>
            <strong>{{ formatTimestamp(activeServer.updated_at) }}</strong>
          </div>
        </div>
        <div class="payload-block raw-block">
          <div class="payload-header">
            <h4>备注</h4>
          </div>
          <pre>{{ activeServer.remark || '无备注' }}</pre>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="服务器名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入服务器名称" />
        </el-form-item>
        <el-form-item label="地址" prop="host">
          <el-input v-model="form.host" placeholder="请输入 IP 或域名" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" controls-position="right" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="可选" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="可选" />
        </el-form-item>
        <el-form-item label="TLS">
          <el-switch v-model="form.tls" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" inline-prompt active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
