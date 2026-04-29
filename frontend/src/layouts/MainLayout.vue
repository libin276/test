<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Connection,
  Collection,
  Document,
  Monitor,
  DataAnalysis,
  Setting,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const menuItems = [
  { index: '/servers', label: '服务器管理', icon: Connection },
  { index: '/topics', label: '订阅管理', icon: Collection },
  { index: '/logs', label: '消息日志', icon: Document },
  { index: '/runtime', label: '运行监控', icon: Monitor },
  { index: '/stats', label: '统计分析', icon: DataAnalysis },
  { index: '/settings', label: '系统设置', icon: Setting },
]

const activeMenu = computed(() => route.path)

function handleSelect(index) {
  router.push(index)
}
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand-block">
        <div class="brand-mark">M</div>
        <div>
          <div class="brand-title">MQTT订阅管理器</div>
          <div class="brand-subtitle">网关与云平台消息排障中心</div>
        </div>
      </div>
    </el-header>
    <el-container>
      <el-aside width="236px" class="app-aside">
        <el-menu
          :default-active="activeMenu"
          class="app-menu"
          @select="handleSelect"
        >
          <el-menu-item
            v-for="item in menuItems"
            :key="item.index"
            :index="item.index"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
