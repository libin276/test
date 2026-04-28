<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings } from '../api'

const loading = ref(false)
const saving = ref(false)
const directionRules = ref([])
const settings = reactive({
  retention_days: 30,
  cleanup_time: '03:00:00',
  export_before_cleanup: true,
})

async function loadSettings() {
  loading.value = true
  try {
    const response = await getSettings()
    settings.retention_days = response.retention_days
    settings.cleanup_time = response.cleanup_time
    settings.export_before_cleanup = response.export_before_cleanup
    directionRules.value = response.direction_rules
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await updateSettings({ ...settings })
    ElMessage.success('设置已保存')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <div class="page-stack">
    <section class="settings-grid" v-loading="loading">
      <div class="content-card">
        <div class="card-header">
          <div>
            <h3>数据保留策略</h3>
            <p>控制消息日志留存周期与自动清理计划</p>
          </div>
        </div>
        <el-form label-width="120px" class="settings-form">
          <el-form-item label="消息保留天数">
            <el-input-number v-model="settings.retention_days" :min="1" :max="365" :step="1" />
          </el-form-item>
          <el-form-item label="自动清理时间">
            <el-input v-model="settings.cleanup_time" placeholder="HH:MM:SS" />
          </el-form-item>
          <el-form-item label="清理前导出">
            <el-switch v-model="settings.export_before_cleanup" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveSettings">保存策略</el-button>
          </el-form-item>
        </el-form>
      </div>
      <div class="content-card">
        <div class="card-header">
          <div>
            <h3>方向判定规则</h3>
            <p>默认按 Topic 关键字自动识别，也支持人工补充规则</p>
          </div>
        </div>
        <el-table :data="directionRules">
          <el-table-column prop="key" label="匹配关键字" min-width="180" />
          <el-table-column prop="type" label="方向" width="100" />
          <el-table-column prop="desc" label="说明" min-width="180" />
        </el-table>
      </div>
    </section>
  </div>
</template>
