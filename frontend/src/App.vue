<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import SettingsDrawer from './components/SettingsDrawer.vue'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || '成长小助手')
const settingsOpen = ref(false)
const today = dayjs().format('M月D日 dddd')

const menus = [
  { path: '/dashboard', label: '看板', emoji: '📊' },
  { path: '/chat', label: '对话打卡', emoji: '💬' },
  { path: '/goals', label: '目标计划', emoji: '🎯' },
  { path: '/schedules', label: '日程', emoji: '📅' },
  { path: '/reviews', label: '复盘', emoji: '📝' },
  { path: '/diaries', label: '日记', emoji: '📔' },
]
</script>

<template>
  <el-container style="height: 100%">
    <el-aside width="200px" class="aside">
      <div class="logo-area">
        <div class="logo-emoji">🌱</div>
        <div>
          <div class="logo-title">成长小助手</div>
          <div class="logo-sub">陪你慢慢变好 ✨</div>
        </div>
      </div>

      <div class="nav">
        <router-link
          v-for="m in menus"
          :key="m.path"
          :to="m.path"
          class="nav-item"
          :class="{ active: route.path === m.path }"
        >
          <span class="nav-emoji">{{ m.emoji }}</span>
          <span>{{ m.label }}</span>
        </router-link>
      </div>

      <div class="aside-footer">
        <span class="footer-emoji">🍀</span>
        <span>数据都在本地哦</span>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header" height="64px">
        <div>
          <div class="header-title">{{ title }}</div>
          <div class="header-date">{{ today }} 也要加油呀 🌟</div>
        </div>
      </el-header>
      <el-main style="padding: 0; background: var(--page-bg)">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 浮动背景装饰 -->
    <div class="bg-decor">
      <span class="decor d1">🌸</span>
      <span class="decor d2">⭐</span>
      <span class="decor d3">🍀</span>
      <span class="decor d4">✨</span>
      <span class="decor d5">🌙</span>
    </div>

    <button class="settings-fab" @click="settingsOpen = true">⚙️</button>
    <SettingsDrawer v-model="settingsOpen" />
  </el-container>
</template>

<style scoped>
.aside {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-soft);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 18px 20px;
}
.logo-emoji {
  font-size: 32px;
  line-height: 1;
}
.logo-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}
.logo-sub {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}
.nav {
  flex: 1;
  padding: 4px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 16px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
}
.nav-item:hover {
  background: #f5f0e8;
  color: var(--text-primary);
}
.nav-item.active {
  background: linear-gradient(135deg, #b8e6d0, #d4f0e2);
  color: #3d8b6a;
  font-weight: 700;
}
.nav-emoji {
  font-size: 17px;
}
.aside-footer {
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-secondary);
  font-size: 11px;
}
.footer-emoji {
  font-size: 14px;
}
.header {
  background: transparent;
  display: flex;
  align-items: center;
  padding: 0 28px;
}
.header-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}
.header-date {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 3px;
}
.settings-fab {
  position: fixed;
  left: 26px;
  bottom: 26px;
  z-index: 100;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  font-size: 22px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(255, 181, 197, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.settings-fab:hover {
  transform: translateY(-3px) rotate(30deg);
  box-shadow: 0 6px 22px rgba(255, 181, 197, 0.55);
}
.bg-decor {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}
.decor {
  position: absolute;
  font-size: 20px;
  opacity: 0.35;
  animation: float-up linear infinite;
}
.d1 { left: 8%; top: 20%; animation-duration: 18s; animation-delay: 0s; }
.d2 { left: 25%; top: 60%; animation-duration: 22s; animation-delay: -4s; font-size: 16px; }
.d3 { left: 60%; top: 15%; animation-duration: 20s; animation-delay: -8s; }
.d4 { left: 80%; top: 50%; animation-duration: 25s; animation-delay: -2s; font-size: 14px; }
.d5 { left: 45%; top: 75%; animation-duration: 19s; animation-delay: -10s; font-size: 18px; }
@keyframes float-up {
  0% { transform: translateY(0) rotate(0deg); opacity: 0; }
  10% { opacity: 0.35; }
  90% { opacity: 0.35; }
  100% { transform: translateY(-120vh) rotate(360deg); opacity: 0; }
}
.page-fade-enter-active {
  transition: all 0.3s ease;
}
.page-fade-leave-active {
  transition: all 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
