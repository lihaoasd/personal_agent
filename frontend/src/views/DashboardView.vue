<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import client from '../api/client'
import GrowthTree from '../components/GrowthTree.vue'
import CountUp from '../components/CountUp.vue'
import Confetti from '../components/Confetti.vue'

const stats = ref<any>(null)
const diaries = ref<any[]>([])
const loading = ref(false)
const confettiTrigger = ref(0)
const prevTotal = ref(0)

const categoryLabels: Record<string, string> = {
  general: '通用', learning: '学习', health: '健康', habit: '习惯',
}

const milestones = [10, 30, 50, 100, 200]

async function load() {
  loading.value = true
  try {
    const [statsRes, diariesRes] = await Promise.all([
      client.get('/stats/dashboard'),
      client.get('/diaries', { params: { limit: 20 } }),
    ])
    diaries.value = diariesRes.data
    const data = statsRes.data
    const crossed = milestones.some((m) => prevTotal.value < m && diaries.value.length >= m)
    if (crossed) confettiTrigger.value++
    prevTotal.value = diaries.value.length
    stats.value = data
  } finally {
    loading.value = false
  }
}

function maxCount(arr: any[]) {
  return Math.max(1, ...arr.map((x) => x.count))
}

import { computed } from 'vue'
const moodStats = computed(() => {
  const map: Record<string, number> = {}
  diaries.value.forEach(d => {
    if (d.mood) map[d.mood] = (map[d.mood] || 0) + 1
  })
  return Object.entries(map).map(([mood, count]) => ({ mood, count }))
})

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">看板 📊</h2>
        <div class="page-subtitle">你的成长数据一览</div>
      </div>
    </div>

    <div v-loading="loading" v-if="stats">
      <!-- 成长小树苗 -->
      <GrowthTree :count="diaries.length" class="tree-card" />

      <!-- 统计卡片 -->
      <div class="stat-grid">
        <div class="stat-card mint">
          <div class="stat-emoji">💬</div>
          <div class="stat-num"><CountUp :value="diaries.length" /></div>
          <div class="stat-label">累计日记</div>
        </div>
        <div class="stat-card peach">
          <div class="stat-emoji">📈</div>
          <div class="stat-num"><CountUp :value="stats.week_days" /><span class="unit">/7</span></div>
          <div class="stat-label">本周打卡</div>
        </div>
        <div class="stat-card pink">
          <div class="stat-emoji">🎯</div>
          <div class="stat-num"><CountUp :value="stats.active_goals" /></div>
          <div class="stat-label">进行中目标</div>
        </div>
        <div class="stat-card lavender">
          <div class="stat-emoji">✅</div>
          <div class="stat-num"><CountUp :value="stats.total_tasks_done" /><span class="unit">/{{ stats.total_tasks }}</span></div>
          <div class="stat-label">任务完成</div>
        </div>
      </div>

      <div class="two-col">
        <div class="panel">
          <div class="panel-title">🎯 目标进度</div>
          <div v-if="!stats.goal_progress.length" class="panel-empty">还没有目标哦～</div>
          <div v-for="g in stats.goal_progress" :key="g.goal_id" class="goal-row">
            <div class="goal-name">
              <span class="goal-dot" :class="g.category"></span>
              {{ g.title }}
              <span class="cat-label">{{ categoryLabels[g.category] }}</span>
            </div>
            <div class="goal-bar-wrap">
              <div class="goal-bar">
                <div class="goal-fill" :class="g.category" :style="{ width: g.total_tasks ? (g.done_tasks / g.total_tasks * 100) + '%' : '0%' }"></div>
              </div>
              <span class="goal-pct">{{ g.done_tasks }}/{{ g.total_tasks }}</span>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-title">😊 心情分布</div>
          <div v-if="!moodStats.length" class="panel-empty">还没有日记～</div>
          <div v-for="m in moodStats" :key="m.mood" class="type-row">
            <span class="type-name">{{ m.mood }}</span>
            <div class="type-bar">
              <div class="type-fill" :style="{ width: (m.count / maxCount(moodStats) * 100) + '%' }"></div>
            </div>
            <span class="type-count">{{ m.count }}</span>
          </div>
        </div>
      </div>

      <div class="panel recent">
        <div class="panel-title">🌟 最近日记</div>
        <div v-if="!diaries.length" class="panel-empty">还没有日记～</div>
        <div v-for="d in diaries.slice(0, 5)" :key="d.id" class="recent-row">
          <span class="recent-date">📅 {{ d.diary_date }}</span>
          <span v-if="d.mood" class="recent-mood">{{ d.mood }}</span>
          <span class="recent-content">{{ d.title || d.content.slice(0, 30) }}</span>
        </div>
      </div>
    </div>

    <Confetti :trigger="confettiTrigger" />
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 18px;
}
.tree-card {
  margin-bottom: 18px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}
.stat-card {
  background: #fff;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-soft);
  padding: 18px;
  position: relative;
  overflow: hidden;
  transition: transform 0.15s;
}
.stat-card:hover {
  transform: translateY(-2px);
}
.stat-card.mint { background: linear-gradient(135deg, #f0f9f4, #fff); }
.stat-card.peach { background: linear-gradient(135deg, #fff5eb, #fff); }
.stat-card.pink { background: linear-gradient(135deg, #fff0f3, #fff); }
.stat-card.lavender { background: linear-gradient(135deg, #f5f0ff, #fff); }
.stat-emoji {
  font-size: 28px;
  margin-bottom: 8px;
}
.stat-num {
  font-size: 30px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.1;
}
.stat-num .unit {
  font-size: 15px;
  color: var(--text-secondary);
  font-weight: 500;
}
.stat-label {
  font-size: 12.5px;
  color: var(--text-secondary);
  margin-top: 4px;
  font-weight: 500;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 18px;
}
.panel {
  background: #fff;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-soft);
  padding: 18px 20px;
}
.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 14px;
}
.panel-empty {
  font-size: 13px;
  color: #c0c0c0;
  padding: 20px 0;
  text-align: center;
}
.goal-row {
  margin-bottom: 12px;
}
.goal-row:last-child { margin-bottom: 0; }
.goal-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}
.goal-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}
.goal-dot.learning { background: #7bc8a4; }
.goal-dot.health { background: #ffb5c5; }
.goal-dot.habit { background: #ffd4a3; }
.goal-dot.general { background: #c0c0c0; }
.cat-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 400;
  background: #f5f0e8;
  padding: 2px 9px;
  border-radius: 10px;
}
.goal-bar-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.goal-bar {
  flex: 1;
  height: 10px;
  background: #f5f0e8;
  border-radius: 6px;
  overflow: hidden;
}
.goal-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.4s ease;
}
.goal-fill.learning { background: linear-gradient(90deg, #7bc8a4, #9dd8ba); }
.goal-fill.health { background: linear-gradient(90deg, #ffb5c5, #ffc9d4); }
.goal-fill.habit { background: linear-gradient(90deg, #ffd4a3, #ffe0ba); }
.goal-fill.general { background: linear-gradient(90deg, #c0c0c0, #d4d4d4); }
.goal-pct {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 700;
  flex-shrink: 0;
}
.type-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.type-row:last-child { margin-bottom: 0; }
.type-name {
  width: 70px;
  font-size: 12.5px;
  color: var(--text-primary);
  flex-shrink: 0;
  font-weight: 500;
}
.type-bar {
  flex: 1;
  height: 12px;
  background: #f5f0e8;
  border-radius: 6px;
  overflow: hidden;
}
.type-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd4a3, #ffb5c5);
  border-radius: 6px;
  transition: width 0.4s ease;
}
.type-count {
  width: 28px;
  text-align: right;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}
.recent {
  margin-bottom: 0;
}
.recent-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px dashed #f0ebe3;
  font-size: 13px;
}
.recent-row:last-child { border-bottom: none; }
.recent-date {
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
  width: 110px;
}
.recent-content {
  flex: 1;
  color: var(--text-primary);
}
.recent-goal {
  font-size: 11px;
  color: #3d8b6a;
  background: #f0f9f4;
  padding: 3px 10px;
  border-radius: 10px;
  flex-shrink: 0;
}
</style>
