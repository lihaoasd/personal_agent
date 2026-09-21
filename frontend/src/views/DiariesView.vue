<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { marked } from 'marked'
import client from '../api/client'

const diaries = ref<any[]>([])
const loading = ref(false)
const selectedDate = ref(new Date().toISOString().slice(0, 10))
const showEditor = ref(false)
const editingDiary = ref<any>(null)
const editorForm = ref({
  title: '',
  content: '',
  mood: '',
  tags: '',
})

const moods = ['😊', '😌', '😴', '😢', '😤', '🤔', '🎉', '💪']
const guideHistory = ref<{ question: string; answer: string }[]>([])
const currentQuestion = ref<{ emoji: string; text: string } | null>(null)
const currentAnswer = ref('')
const guideLoading = ref(false)
const diaryId = ref<number | null>(null)

function renderMarkdown(text: string) {
  return marked(text || '')
}

const filteredDiaries = computed(() => {
  return diaries.value.filter(d => d.diary_date === selectedDate.value)
})

async function loadDiaries() {
  loading.value = true
  try {
    const { data } = await client.get('/diaries', { params: { limit: 200 } })
    diaries.value = data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingDiary.value = null
  guideHistory.value = []
  currentQuestion.value = null
  currentAnswer.value = ''
  diaryId.value = null
  editorForm.value = { title: '', content: '', mood: '', tags: '' }
  showEditor.value = true
}

function openEdit(d: any) {
  editingDiary.value = d
  diaryId.value = d.id
  guideHistory.value = []
  currentQuestion.value = null
  currentAnswer.value = ''
  editorForm.value = {
    title: d.title || '',
    content: d.content || '',
    mood: d.mood || '',
    tags: d.tags || '',
  }
  showEditor.value = true
}

async function saveDiary() {
  let content = editorForm.value.content
  let title = editorForm.value.title
  const payload = { ...editorForm.value, content, title }
  if (editingDiary.value) {
    await client.put(`/diaries/${diaryId.value}`, payload)
  } else {
    const res = await client.post('/diaries', {
      diary_date: selectedDate.value,
      ...payload,
    })
    diaryId.value = res.data.id
  }

  // 生成第一个引导问题
  guideLoading.value = true
  try {
    const res = await client.post('/diaries/next-guide', {
      content,
      history: [],
    })
    if (res.data.has_next && res.data.question) {
      currentQuestion.value = res.data.question
    } else {
      // 没有问题了，直接完成
      showEditor.value = false
      await loadDiaries()
    }
  } catch (e) {
    console.error('生成引导问题失败', e)
    showEditor.value = false
    await loadDiaries()
  }
  guideLoading.value = false
}

// 回答当前问题，生成下一个
async function answerGuide() {
  if (!currentQuestion.value) return
  const ans = currentAnswer.value.trim()
  if (!ans) return

  // 加入历史
  guideHistory.value.push({
    question: currentQuestion.value.text,
    answer: ans,
  })

  guideLoading.value = true
  currentAnswer.value = ''

  try {
    const res = await client.post('/diaries/next-guide', {
      content: editorForm.value.content,
      history: guideHistory.value,
    })
    if (res.data.has_next && res.data.question) {
      currentQuestion.value = res.data.question
    } else {
      // 没有问题了，合并内容保存
      await finishGuide()
    }
  } catch (e) {
    console.error('生成下一个问题失败', e)
    await finishGuide()
  }
  guideLoading.value = false
}

// 完成引导，合并内容
async function finishGuide() {
  let content = editorForm.value.content
  const lines = guideHistory.value.map((h) => {
    return `## 💭 ${h.question}\n\n${h.answer}`
  })
  if (lines.length > 0) {
    content += '\n\n---\n\n' + lines.join('\n\n')
  }

  await client.put(`/diaries/${diaryId.value}`, {
    ...editorForm.value,
    content,
  })
  showEditor.value = false
  await loadDiaries()
}

async function deleteDiary(id: number) {
  await client.delete(`/diaries/${id}`)
  await loadDiaries()
}

function selectDate(date: string) {
  selectedDate.value = date
}

const calendarDays = computed(() => {
  const today = new Date(selectedDate.value)
  const year = today.getFullYear()
  const month = today.getMonth()
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startWeekday = firstDay.getDay() || 7
  const days: { date: string; day: number; hasDiary: boolean; isToday: boolean }[] = []

  for (let i = startWeekday - 1; i > 0; i--) {
    const d = new Date(year, month, 1 - i)
    days.push({
      date: d.toISOString().slice(0, 10),
      day: d.getDate(),
      hasDiary: false,
      isToday: false,
    })
  }

  const todayStr = new Date().toISOString().slice(0, 10)
  for (let i = 1; i <= lastDay.getDate(); i++) {
    const d = new Date(year, month, i)
    const dateStr = d.toISOString().slice(0, 10)
    days.push({
      date: dateStr,
      day: i,
      hasDiary: diaries.value.some(d => d.diary_date === dateStr),
      isToday: dateStr === todayStr,
    })
  }

  return days
})

onMounted(loadDiaries)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">日记 📔</h2>
        <div class="page-subtitle">记录每天的小确幸和小心情</div>
      </div>
      <button class="btn-primary" @click="openCreate">✍️ 写日记</button>
    </div>

    <div class="diary-layout">
      <div class="calendar-card">
        <div class="calendar-header">
          <span class="month-label">{{ selectedDate.slice(0, 7) }}</span>
        </div>
        <div class="calendar-grid">
          <div class="weekday">一</div>
          <div class="weekday">二</div>
          <div class="weekday">三</div>
          <div class="weekday">四</div>
          <div class="weekday">五</div>
          <div class="weekday">六</div>
          <div class="weekday">日</div>
          <div
            v-for="(d, i) in calendarDays"
            :key="i"
            class="calendar-day"
            :class="{
              active: d.date === selectedDate,
              today: d.isToday,
              'has-diary': d.hasDiary,
            }"
            @click="selectDate(d.date)"
          >
            {{ d.day }}
            <span v-if="d.hasDiary" class="diary-dot">●</span>
          </div>
        </div>
      </div>

      <div class="diary-content" v-loading="loading">
        <div v-if="!filteredDiaries.length" class="empty-state">
          <div class="empty-emoji">🌱</div>
          <div>这一天还没有日记</div>
          <div class="empty-hint">点「写日记」记录一下今天吧～</div>
        </div>

        <div v-for="d in filteredDiaries" :key="d.id" class="diary-card">
          <div class="diary-head">
            <span v-if="d.mood" class="diary-mood">{{ d.mood }}</span>
            <div class="diary-title">{{ d.title || '无标题' }}</div>
            <div class="diary-actions">
              <button class="icon-btn" @click="openEdit(d)">✏️</button>
              <button class="icon-btn" @click="deleteDiary(d.id)">🗑️</button>
            </div>
          </div>
          <div v-if="d.tags" class="diary-tags">
            <span v-for="tag in d.tags.split(',').filter(Boolean)" :key="tag" class="tag">#{{ tag.trim() }}</span>
          </div>
          <div class="diary-body" v-html="renderMarkdown(d.content)"></div>
        </div>
      </div>
    </div>

    <!-- 写日记弹窗 -->
    <el-dialog v-model="showEditor" width="650px" class="diary-dialog">
      <template #header>
        <div class="dialog-header">
          <span class="header-emoji">✍️</span>
          <span class="header-title">{{ editingDiary ? '编辑日记' : '写日记' }}</span>
          <span class="header-date">{{ selectedDate }}</span>
        </div>
      </template>

      <div class="editor-form">
        <div class="form-row">
          <label>标题</label>
          <el-input v-model="editorForm.title" placeholder="给今天起个标题..." />
        </div>

        <div class="form-row">
          <label>内容</label>
          <el-input
            v-model="editorForm.content"
            type="textarea"
            :rows="6"
            placeholder="今天发生了什么？有什么感想？随便写写～"
            :disabled="currentQuestion"
          />
        </div>

        <!-- 引导问题（苏格拉底式，动态生成） -->
        <div v-if="guideLoading" class="guide-loading">
          <div class="loading-spinner"></div>
          <div class="loading-text">正在思考一个好问题...</div>
        </div>

        <div v-if="currentQuestion && !guideLoading" class="guide-step">
          <div class="guide-divider">--- 💭 觉察一下 ---</div>
          <div class="guide-progress">第 {{ guideHistory.length + 1 }} 问</div>
          <div class="guide-question">
            <span class="q-emoji">{{ currentQuestion.emoji }}</span>
            <span class="q-text">{{ currentQuestion.text }}</span>
          </div>
          <el-input
            v-model="currentAnswer"
            type="textarea"
            :rows="3"
            placeholder="随便写点什么，跟着感觉走..."
            @keyup.enter="answerGuide"
          />
          <div class="guide-actions">
            <button class="answer-btn" @click="answerGuide">回答 →</button>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="cancel-btn" @click="showEditor = false">取消</button>
          <button v-if="!currentQuestion" class="save-btn" @click="saveDiary">
            {{ guideLoading ? '保存中...' : '保存 🎀' }}
          </button>
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
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(180, 165, 224, 0.4);
}

.diary-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 140px);
}

.calendar-card {
  width: 280px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid var(--border-soft);
  border-radius: 20px;
  padding: 20px;
}
.calendar-header {
  text-align: center;
  margin-bottom: 16px;
}
.month-label {
  font-size: 16px;
  font-weight: 700;
  color: #5a4a8a;
}
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.weekday {
  text-align: center;
  font-size: 11px;
  color: #b0a090;
  padding: 4px 0;
  font-weight: 600;
}
.calendar-day {
  position: relative;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  color: #5a4a3a;
}
.calendar-day:hover {
  background: #f5f0e8;
}
.calendar-day.active {
  background: #d4c5f0;
  color: #fff;
  font-weight: 700;
}
.calendar-day.today {
  border: 2px solid #7bc8a4;
}
.calendar-day.has-diary::after {
  content: '●';
  position: absolute;
  bottom: 2px;
  right: 4px;
  font-size: 8px;
  color: #7bc8a4;
}
.calendar-day.active.has-diary::after {
  color: #fff;
}
.diary-dot {
  position: absolute;
  bottom: 2px;
  right: 4px;
  font-size: 8px;
  color: #7bc8a4;
}

.diary-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.diary-card {
  background: #fff;
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  padding: 18px 20px;
  transition: transform 0.15s;
}
.diary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(180, 160, 130, 0.1);
}
.diary-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.diary-mood {
  font-size: 20px;
}
.diary-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
}
.diary-actions {
  display: flex;
  gap: 6px;
}
.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.icon-btn:hover {
  opacity: 1;
}
.diary-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.tag {
  font-size: 12px;
  color: #5a4a8a;
  background: #f5f0ff;
  padding: 3px 10px;
  border-radius: 10px;
}
.diary-body {
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--text-primary);
}

.diary-dialog :deep(.el-dialog) {
  border-radius: 24px;
  padding: 0;
  overflow: hidden;
}
.diary-dialog :deep(.el-dialog__header) {
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
.header-date {
  margin-left: auto;
  font-size: 13px;
  color: var(--text-secondary);
}
.diary-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}
.editor-form {
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

.mood-picker {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.mood-option {
  font-size: 24px;
  padding: 6px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
  border: 2px solid transparent;
}
.mood-option:hover {
  background: #f5f0e8;
}
.mood-option.active {
  background: #f5f0ff;
  border-color: #b8a5e0;
  transform: scale(1.1);
}
.diary-dialog :deep(.el-input__wrapper),
.diary-dialog :deep(.el-textarea__inner) {
  border-radius: 14px;
  background: #faf6f0;
  box-shadow: none;
  border: 1px solid var(--border-soft);
  padding: 8px 14px;
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

/* 引导步骤 */
.guide-loading {
  text-align: center;
  padding: 30px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e8e0f5;
  border-top-color: #b8a5e0;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-text {
  color: var(--text-secondary);
  font-size: 13.5px;
}
.guide-step {
  background: #faf6ff;
  border: 1px solid #e8e0f5;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.guide-divider {
  text-align: center;
  font-size: 12.5px;
  color: #b8a5e0;
}
.guide-progress {
  font-size: 12px;
  color: var(--text-secondary);
}
.guide-question {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14.5px;
  font-weight: 600;
  color: #5a4a8a;
}
.q-emoji {
  font-size: 20px;
}
.guide-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.skip-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 12.5px;
  cursor: pointer;
}
.answer-btn {
  padding: 8px 18px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #b8a5e0, #a895d0);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.answer-btn:hover {
  transform: translateY(-1px);
}
</style>
