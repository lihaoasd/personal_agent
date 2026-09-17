<script setup lang="ts">
import { onMounted, ref } from 'vue'
import client from '../api/client'

const reviews = ref<any[]>([])
const loading = ref(false)
const generating = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/reviews')
    reviews.value = data
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true
  try {
    await client.post('/reviews/generate')
    await load()
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">周复盘 📝</h2>
        <div class="page-subtitle">每周回顾，看见自己的成长轨迹</div>
      </div>
      <button class="btn-primary" :disabled="generating" @click="generate">
        {{ generating ? '思考中…' : '✨ 生成本周复盘' }}
      </button>
    </div>

    <div v-loading="loading" class="review-list">
      <div v-if="!reviews.length" class="empty-state">
        <div class="empty-emoji">📖</div>
        <div>还没有复盘记录</div>
        <div class="empty-hint">点「生成本周复盘」，AI 会基于你的记录生成总结～</div>
      </div>

      <div v-for="r in reviews" :key="r.id" class="review-card">
        <div class="review-head">
          <div class="review-period">
            <span class="period-emoji">📅</span>
            {{ r.period_start }} ~ {{ r.period_end }}
          </div>
          <span class="review-time">{{ r.generated_at }}</span>
        </div>
        <div class="review-content">{{ r.content }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 12px;
}
.btn-primary {
  padding: 9px 22px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #d4c5f0, #b8a5e0);
  color: #5a4a8a;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(180, 165, 224, 0.4);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.review-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}
.empty-emoji {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-hint {
  font-size: 12.5px;
  margin-top: 6px;
  color: #c0c0c0;
}
.review-card {
  background: #fff;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-soft);
  padding: 20px 22px;
  transition: transform 0.15s;
}
.review-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(180, 160, 130, 0.1);
}
.review-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed #f0ebe3;
}
.review-period {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14.5px;
  font-weight: 700;
  color: #5a4a8a;
}
.period-emoji {
  font-size: 16px;
}
.review-time {
  font-size: 12px;
  color: var(--text-secondary);
}
.review-content {
  font-size: 13.5px;
  line-height: 1.9;
  color: var(--text-primary);
  white-space: pre-wrap;
}
</style>
