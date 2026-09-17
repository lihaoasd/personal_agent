<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import client from '../api/client'

const reviews = ref<any[]>([])
const loading = ref(false)
const generating = ref(false)
const selectedId = ref<number | null>(null)
const writingVisible = ref(false)
const writeForm = ref({ period_start: '', period_end: '', content: '' })

const selectedReview = computed(() =>
  reviews.value.find(r => r.id === selectedId.value) || reviews.value[0] || null
)

// 渲染 markdown
function renderMd(text: string) {
  return marked.parse(text || '', { async: false }) as string
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/reviews')
    reviews.value = data
    if (!selectedId.value && reviews.value.length) {
      selectedId.value = reviews.value[0].id
    }
  } finally {
    loading.value = false
  }
}

async function generate() {
  generating.value = true
  try {
    await client.post('/reviews/generate', {})
    await load()
  } finally {
    generating.value = false
  }
}

function openWrite() {
  // 默认填本周日期
  const now = new Date()
  const monday = new Date(now)
  monday.setDate(now.getDate() - now.getDay() + 1)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  writeForm.value = {
    period_start: fmt(monday),
    period_end: fmt(sunday),
    content: '',
  }
  writingVisible.value = true
}

async function saveWrite() {
  if (!writeForm.value.content.trim()) return
  await client.post('/reviews', writeForm.value)
  writingVisible.value = false
  await load()
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
      <div class="head-actions">
        <button class="write-btn" @click="openWrite">✍️ 写复盘</button>
        <button class="btn-primary" :disabled="generating" @click="generate">
          {{ generating ? '思考中…' : '✨ AI 生成复盘' }}
        </button>
      </div>
    </div>

    <div v-loading="loading" class="review-layout">
      <!-- 左侧：复盘列表 -->
      <div class="review-sidebar">
        <div v-if="!reviews.length" class="empty-state">
          <div class="empty-emoji">📖</div>
          <div>还没有复盘记录</div>
          <div class="empty-hint">点「生成本周复盘」试试～</div>
        </div>
        <div
          v-for="r in reviews"
          :key="r.id"
          class="review-item"
          :class="{ active: r.id === selectedId }"
          @click="selectedId = r.id"
        >
          <div class="item-title">{{ r.title || `${r.period_start} ~ ${r.period_end}` }}</div>
          <div class="item-time">{{ r.period_start }} ~ {{ r.period_end }}</div>
        </div>
      </div>

      <!-- 右侧：复盘详情 -->
      <div class="review-detail">
        <div v-if="!selectedReview" class="detail-empty">
          <div class="empty-emoji">📝</div>
          <div>选左边的复盘查看详情</div>
        </div>
        <div v-else class="review-card">
          <div class="review-head">
            <div class="review-period">
              <span class="period-emoji">📅</span>
              {{ selectedReview.period_start }} ~ {{ selectedReview.period_end }}
            </div>
            <span class="review-time">{{ selectedReview.generated_at }}</span>
          </div>
          <div class="review-content" v-html="renderMd(selectedReview.content)"></div>
        </div>
      </div>
    </div>

    <!-- 写复盘弹窗 -->
    <el-dialog v-model="writingVisible" width="600px" class="write-dialog">
      <template #header>
        <div class="dialog-header">
          <span class="header-emoji">✍️</span>
          <span class="header-title">写周复盘</span>
        </div>
      </template>
      <div class="write-form">
        <div class="form-row">
          <label>周期</label>
          <div class="date-range">
            <el-input v-model="writeForm.period_start" placeholder="开始日期" />
            <span class="sep">~</span>
            <el-input v-model="writeForm.period_end" placeholder="结束日期" />
          </div>
        </div>
        <div class="form-row">
          <label>复盘内容</label>
          <el-input
            v-model="writeForm.content"
            type="textarea"
            :rows="12"
            placeholder="这周发生了什么？有什么收获？下周想怎么做？随便写写～"
          />
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <button class="cancel-btn" @click="writingVisible = false">取消</button>
          <button class="save-btn" @click="saveWrite">保存 🎀</button>
        </div>
      </template>
    </el-dialog>
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
.head-actions {
  display: flex;
  gap: 10px;
}
.write-btn {
  padding: 9px 20px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: #fff;
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.write-btn:hover {
  border-color: #b8a5e0;
  background: #f5f0ff;
  color: #5a4a8a;
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
.review-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 140px);
}
.review-sidebar {
  width: 260px;
  flex-shrink: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.review-item {
  background: #fff;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
}
.review-item:hover {
  border-color: #d4c5f0;
  transform: translateX(2px);
}
.review-item.active {
  background: #f5f0ff;
  border-color: #b8a5e0;
}
.item-title {
  font-size: 13px;
  font-weight: 700;
  color: #5a4a8a;
  margin-bottom: 4px;
  line-height: 1.4;
}
.item-time {
  font-size: 11.5px;
  color: var(--text-secondary);
}
.review-detail {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}
.detail-empty {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-secondary);
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
}
/* markdown 样式 */
.review-content :deep(h2) {
  font-size: 16px;
  font-weight: 700;
  color: #5a4a8a;
  margin: 16px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0ebe3;
}
.review-content :deep(h2:first-child) {
  margin-top: 0;
}
.review-content :deep(ul) {
  padding-left: 20px;
  margin: 8px 0;
}
.review-content :deep(li) {
  margin: 4px 0;
}
.review-content :deep(strong) {
  color: #5a4a8a;
  font-weight: 700;
}
.review-content :deep(p) {
  margin: 8px 0;
}
.review-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}
.review-content :deep(ol li) {
  margin: 6px 0;
}

/* 写复盘弹窗 */
.write-dialog :deep(.el-dialog) {
  border-radius: 24px;
  padding: 0;
  overflow: hidden;
}
.write-dialog :deep(.el-dialog__header) {
  padding: 0;
  margin: 0;
}
.dialog-header {
  background: linear-gradient(135deg, #f5f0ff, #fff9f2);
  padding: 20px 24px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-emoji {
  font-size: 24px;
}
.header-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}
.write-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}
.write-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-row label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}
.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}
.date-range .el-input {
  flex: 1;
}
.date-range .sep {
  color: var(--text-secondary);
}
.write-dialog :deep(.el-input__wrapper),
.write-dialog :deep(.el-textarea__inner) {
  border-radius: 14px;
  background: #faf6f0;
  box-shadow: none;
  border: 1px solid var(--border-soft);
  padding: 8px 14px;
}
.write-dialog :deep(.el-textarea__inner) {
  line-height: 1.7;
}
.dialog-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 0 24px 20px;
}
.cancel-btn {
  padding: 9px 20px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: #fff;
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}
.cancel-btn:hover {
  background: #faf6f0;
}
.save-btn {
  padding: 9px 22px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #d4c5f0, #b8a5e0);
  color: #5a4a8a;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
}
.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(180, 165, 224, 0.4);
}
</style>
