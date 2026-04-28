import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import ServersPage from '../pages/ServersPage.vue'
import TopicsPage from '../pages/TopicsPage.vue'
import LogsPage from '../pages/LogsPage.vue'
import RuntimePage from '../pages/RuntimePage.vue'
import StatsPage from '../pages/StatsPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/servers',
      children: [
        { path: '/servers', name: 'servers', component: ServersPage },
        { path: '/topics', name: 'topics', component: TopicsPage },
        { path: '/logs', name: 'logs', component: LogsPage },
        { path: '/runtime', name: 'runtime', component: RuntimePage },
        { path: '/stats', name: 'stats', component: StatsPage },
        { path: '/settings', name: 'settings', component: SettingsPage },
      ],
    },
  ],
})

export default router
