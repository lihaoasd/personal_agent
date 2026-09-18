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

const templates = [
  {
    key: 'free',
    label: '自由书写',
    emoji: '✍️',
    desc: '想到什么写什么，自由倾诉',
  },
  {
    key: 'emotion',
    label: '情绪觉察',
    emoji: '💭',
    desc: '读懂自己的情绪，理解自己',
    questions: [
      { key: 'q1', emoji: '😌', text: '今天整体心情怎么样？', placeholder: '比如：平静 / 有点烦躁 / 开心...' },
      { key: 'q2', emoji: '📍', text: '发生了什么事？', placeholder: '具体描述一下触发你情绪的那件事...' },
      { key: 'q3', emoji: '💡', text: '这件事让你想到了什么？', placeholder: '背后的原因、你的期待、或者你的模式...' },
      { key: 'q4', emoji: '🌱', text: '下次遇到可以怎么做？', placeholder: '给自己一个小建议...' },
    ],
  },
  {
    key: 'review',
    label: '三省吾身',
    emoji: '🌱',
    desc: '每日反思，持续成长',
    questions: [
      { key: 'q1', emoji: '✅', text: '今天做得好的一件事？', placeholder: '哪怕很小的事也值得记录...' },
      { key: 'q2', emoji: '🤔', text: '今天可以改进的一件事？', placeholder: '不用自责，只是观察...' },
      { key: 'q3', emoji: '💡', text: '今天学到了什么？', placeholder: '一个道理、一个技巧、或者一个感悟...' },
      { key: 'q4', emoji: '🎯', text: '明天最重要的一件事？', placeholder: '只挑一件，聚焦最重要的...' },
    ],
  },
]

const selectedTemplate = ref('free')
const guideAnswers = ref<Record<string, string>>({})
const isGuided = ref(true)  // 是否是引导模式

function applyTemplate(key: string) {
  selectedTemplate.value = key
  guideAnswers.value = {}
  const t = templates.find(x => x.key === key)
  if (t && t.questions) {
    isGuided.value = true
  } else {
    isGuided.value = false
  }
}

function buildContent() {
  // 引导模式：把问答拼接成内容
  if (!isGuided.value) return editorForm.value.content
  const t = templates.find(x => x.key === selectedTemplate.value)
  if (!t || !t.questions) return editorForm.value.content
  const lines = t.questions.map((q, i) => {
    const ans = guideAnswers.value[q.key] || ''
    if (!ans) return ''
    return `## ${q.emoji} ${q.text}\n\n${ans}`
  }).filter(Boolean)
  return lines.join('\n\n')
}

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
  selectedTemplate.value = 'free'
  isGuided.value = false
  guideAnswers.value = {}
  editorForm.value = { title: '', content: '', mood: '', tags: '' }
  showEditor.value = true
}

function openEdit(d: any) {
  editingDiary.value = d
  editorForm.value = {
    title: d.title || '',
    content: d.content || '',
    mood: d.mood || '',
    tags: d.tags || '',
  }
  showEditor.value = true
}

async function saveDiary() {
  const content = buildContent()
  // 自动生成标题
  let title = editorForm.value.title
  if (!title) {
    const t = templates.find(x => x.key === selectedTemplate.value)
    if (t && t.key !== 'free') {
      title = t.label + ' · ' + selectedDate.value.slice(5)
    } else if (content) {
      title = content.replace(/\n/g, ' ').slice(0, 15)
    }
  }
  const payload = { ...editorForm.value, content, title }
  if (editingDiary.value) {
    await client.put(`/diaries/${editingDiary.value.id}`, payload)
  } else {
    await client.post('/diaries', {
      diary_date: selectedDate.value,
      ...payload,
    })
  }
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

// 生成日历（当月）
const calendarDays = computed(() => {
  const today = new Date(selectedDate.value)
  const year = today.getFullYear()
  const month = today.getMonth()
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startWeekday = firstDay.getDay() || 7 // 周一为1
  const days: { date: string; day: number; hasDiary: boolean; isToday: boolean }[] = []

  // 上月补位
  for (let i = startWeekday - 1; i > 0; i--) {
    const d = new Date(year, month, 1 - i)
    days.push({
      date: d.toISOString().slice(0, 10),
      day: d.getDate(),
      hasDiary: false,
      isToday: false,
    })
  }

  // 本月
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
      <!-- 左边：日历 -->
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

      <!-- 右边：当天日记列表 -->
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
    <el-dialog v-model="showEditor" width="600px" class="diary-dialog">
      <template #header>
        <div class="dialog-header">
          <span class="header-emoji">✍️</span>
          <span class="header-title">{{ editingDiary ? '编辑日记' : '写日记' }}</span>
          <span class="header-date">{{ selectedDate }}</span>
        </div>
      </template>

      <div class="editor-form">
        <!-- 第一步：选模板 -->
        <div class="form-row">
          <label>今天想写点什么？</label>
          <div class="template-picker">
            <div
              v-for="t in templates"
              :key="t.key"
              class="template-card"
              :class="{ active: selectedTemplate === t.key }"
              @click="applyTemplate(t.key)"
            >
              <div class="template-emoji">{{ t.emoji }}</div>
              <div class="template-label">{{ t.label }}</div>
              <div class="template-desc">{{ t.desc }}</div>
            </div>
          </div>
        </div>

        <!-- 第二步：心情 -->
        <div class="form-row">
          <label>心情</label>
          <div class="mood-picker">
            <span
              v-for="m in moods"
              :key="m"
              class="mood-option"
              :class="{ active: editorForm.mood === m }"
              @click="editorForm.mood = m"
            >{{ m }}</span>
          </div>
        </div>

        <!-- 第三步：引导问答模式 -->
        <template v-if="isGuided && selectedTemplate !== 'free'">
          <div
            v-for="(q, i) in templates.find(t => t.key === selectedTemplate)?.questions"
            :key="q.key"
            class="question-row"
          >
            <div class="question-text">
              <span class="q-emoji">{{ q.emoji }}</span>
              <span class="q-text">{{ i + 1 }}. {{ q.text }}</span>
            </div>
            <el-input
              v-model="guideAnswers[q.key]"
              type="textarea"
              :rows="2"
              :placeholder="q.placeholder"
            />
          </div>
        </template>

        <!-- 自由编辑模式才显示内容输入框 -->
        <div v-if="!isGuided || selectedTemplate === 'free'" class="form-row">
          <label>内容</label>
          <el-input
            v-model="editorForm.content"
            type="textarea"
            :rows="6"
            placeholder="今天发生了什么？有什么感想？随便写写～"
          />
        </div>

        <!-- 切换模式按钮（只有一个） -->
        <div v-if="selectedTemplate !== 'free'" class="form-row">
          <button class="free-toggle" @click="isGuided = !isGuided">
            {{ isGuided ? '✏️ 切换到自由编辑模式' : '💡 回到引导模式' }}
          </button>
        </div>

        <div class="form-row">
          <label>标签（逗号分隔）</label>
          <el-input v-model="editorForm.tags" placeholder="比如：运动, 阅读, 开心" />
        </div>

      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="cancel-btn" @click="showEditor = false">取消</button>
          <button class="save-btn" @click="saveDiary">保存 🎀</button>
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

/* 左边日历 */
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

/* 右边日记列表 */
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
  white-space: pre-wrap;
}

/* 弹窗 */
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
.template-picker {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.template-card {
  flex: 1;
  min-width: 120px;
  padding: 14px;
  border-radius: 16px;
  background: #faf6f0;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
}
.template-card:hover {
  background: #f5f0e8;
}
.template-card.active {
  background: #f5f0ff;
  border-color: #b8a5e0;
}
.template-emoji {
  font-size: 24px;
  margin-bottom: 6px;
}
.template-label {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.template-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.question-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  background: #faf6f0;
  border-radius: 14px;
}
.question-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}
.q-emoji {
  font-size: 18px;
}
.free-toggle {
  background: none;
  border: none;
  color: #b8a5e0;
  font-size: 12.5px;
  cursor: pointer;
  text-align: center;
  padding: 8px;
  transition: opacity 0.15s;
}
.free-toggle:hover {
  opacity: 0.7;
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
</style>
