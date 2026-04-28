<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTopic,
  deleteTopic,
  getServers,
  getTopics,
  toggleTopic,
  updateTopic,
} from '../api'

const loading = ref(false)
const submitting = ref(false)
const tableData = ref([])
const serverOptions = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)
const editingId = ref(null)

const filters = reactive({
  serverId: '',
  keyword: '',
  direction: '',
  enabled: '',
})

const form = reactive({
  server_id: undefined,
  topic: '',
  qos: 0,
  direction: '',
  enabled: true,
  remark: '',
})

const rules = {
  server_id: [{ required: true, message: '请选择所属服务器', trigger: 'change' }],
  topic: [{ required: true, message: '请输入 Topic', trigger: 'blur' }],
}

function resetForm() {
  Object.assign(form, {
    server_id: undefined,
    topic: '',
    qos: 0,
    direction: '',
    enabled: true,
    remark: '',
  })
  editingId.value = null
}

async function loadServerOptions() {
  try {
    serverOptions.value = await getServers()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function loadTopics() {
  loading.value = true
  try {
    tableData.value = await getTopics({
      server_id: filters.serverId || undefined,
      keyword: filters.keyword,
      direction: filters.direction,
      enabled: filters.enabled === '' ? undefined : filters.enabled,
    })
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filters.serverId = ''
  filters.keyword = ''
  filters.direction = ''
  filters.enabled = ''
  loadTopics()
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  editingId.value = row.id
  Object.assign(form, {
    server_id: row.server_id,
    topic: row.topic,
    qos: row.qos,
    direction: row.direction || '',
    enabled: row.enabled,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      ...form,
      direction: form.direction || null,
      remark: form.remark || null,
    }
    if (editingId.value) {
      await updateTopic(editingId.value, payload)
      ElMessage.success('Topic 已更新')
    } else {
      await createTopic(payload)
      ElMessage.success('Topic 已创建')
    }
    dialogVisible.value = false
    resetForm()
    loadTopics()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    submitting.value = false
  }
}

async function handleToggle(row, value) {
  try {
    const updated = await toggleTopic(row.id, value)
    Object.assign(row, updated)
    ElMessage.success(value ? 'Topic 已启用' : 'Topic 已禁用')
  } catch (error) {
    row.enabled = !value
    ElMessage.error(error.message)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除 Topic“${row.topic}”吗？`, '删除确认', {
      type: 'warning',
    })
    await deleteTopic(row.id)
    ElMessage.success('Topic 已删除')
    loadTopics()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

onMounted(async () => {
  await loadServerOptions()
  await loadTopics()
})
</script>

<template>
  <div class="page-stack">
    <section class="toolbar-card soft-blue">
      <div class="card-header split-header">
        <div>
          <h3>订阅 Topic 管理</h3>
          <p>按服务器集中管理订阅项，并支持手动指定上下行方向</p>
        </div>
        <el-button type="primary" @click="openCreateDialog">新增 Topic</el-button>
      </div>
      <div class="toolbar-grid wide">
        <el-select v-model="filters.serverId" placeholder="所属服务器" clearable>
          <el-option
            v-for="item in serverOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="搜索 Topic" clearable />
        <el-select v-model="filters.direction" placeholder="方向" clearable>
          <el-option label="上行" value="上行" />
          <el-option label="下行" value="下行" />
        </el-select>
        <el-select v-model="filters.enabled" placeholder="启用状态" clearable>
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
        <el-button type="primary" @click="loadTopics">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
    </section>

    <section class="content-card">
      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column prop="server_name" label="所属服务器" width="160" />
        <el-table-column prop="topic" label="Topic" min-width="280" show-overflow-tooltip />
        <el-table-column prop="qos" label="QoS" width="80" />
        <el-table-column label="方向" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.direction === '上行' ? 'success' : 'warning'">{{ scope.row.direction }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="启用" width="90">
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
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" fixed="right" width="220">
          <template #default="scope">
            <el-button link type="primary">详情</el-button>
            <el-button link type="primary" @click="openEditDialog(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 Topic' : '新增 Topic'" width="520px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="所属服务器" prop="server_id">
          <el-select v-model="form.server_id" placeholder="请选择服务器">
            <el-option
              v-for="item in serverOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Topic" prop="topic">
          <el-input v-model="form.topic" placeholder="请输入订阅 Topic" />
        </el-form-item>
        <el-form-item label="QoS">
          <el-select v-model="form.qos">
            <el-option :value="0" label="0" />
            <el-option :value="1" label="1" />
            <el-option :value="2" label="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="方向">
          <el-select v-model="form.direction" placeholder="留空则自动判定" clearable>
            <el-option label="上行" value="上行" />
            <el-option label="下行" value="下行" />
          </el-select>
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
