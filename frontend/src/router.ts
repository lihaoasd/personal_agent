import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/chat', component: () => import('./views/ChatView.vue'), meta: { title: '对话打卡' } },
    { path: '/goals', component: () => import('./views/GoalsView.vue'), meta: { title: '目标计划' } },
    { path: '/schedules', component: () => import('./views/SchedulesView.vue'), meta: { title: '日程' } },
    { path: '/reviews', component: () => import('./views/ReviewsView.vue'), meta: { title: '复盘' } },
    { path: '/diaries', component: () => import('./views/DiariesView.vue'), meta: { title: '日记' } },
    { path: '/dashboard', component: () => import('./views/DashboardView.vue'), meta: { title: '看板' } },
  ],
})

export default router
