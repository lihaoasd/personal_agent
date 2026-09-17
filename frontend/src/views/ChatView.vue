<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import client from '../api/client'

const messages = ref<any[]>([])
const templates = ref<any[]>([])
const input = ref('')
const sending = ref(false)
const weekDays = ref(0)
const todayDone = ref(false)
const listRef = ref<HTMLElement>()
const currentSessionId = ref<number | null>(null)
const loadingMore = ref(false)
const hasMore = ref(true)
const showSessions = ref(false)
const sessions = ref<any[]>([])
const editingSessionId = ref<number | null>(null)
const editTitleInput = ref('')
const deletingSessionId = ref<number | null>(null)

let pollTimer: number | undefined
let notifiedToday = false

async function loadMessages(initial = true) {
  if (!currentSessionId.value) return
  if (initial) {
    // 初始加载最新 50 条
    const { data } = await client.get('/chat/messages', {
      params: { session_id: currentSessionId.value, limit: 50 },
    })
    messages.value = data.map((m: any) => ({ ...m, display: m.content }))
    hasMore.value = data.length >= 50
    // 直接跳到最底部
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
      })
    })
  } else {
    // 加载更早的消息（滚动到顶部时）
    if (!hasMore.value || loadingMore.value) return
    loadingMore.value = true
    const firstId = messages.value[0]?.id
    const { data } = await client.get('/chat/messages', {
      params: { session_id: currentSessionId.value, limit: 30, before_id: firstId },
    })
    if (data.length < 30) hasMore.value = false
    // 插入到列表前面
    const oldHeight = listRef.value?.scrollHeight || 0
    messages.value.unshift(...data.map((m: any) => ({ ...m, display: m.content })))
    // 保持滚动位置不变
    requestAnimationFrame(() => {
      if (listRef.value) {
        const newHeight = listRef.value.scrollHeight
        listRef.value.scrollTop = newHeight - oldHeight
      }
    })
    loadingMore.value = false
  }
}

function onScroll() {
  if (!listRef.value) return
  // 滚动到顶部时加载更多
  if (listRef.value.scrollTop < 50 && hasMore.value && !loadingMore.value) {
    loadMessages(false)
  }
}

async function loadSessions() {
  const { data } = await client.get('/chat/sessions')
  sessions.value = data
}

async function newChat() {
  // 只重置前端状态，不创建会话，等发第一条消息时才创建
  currentSessionId.value = null
  messages.value = []
  hasMore.value = true
}

async function switchSession(id: number) {
  currentSessionId.value = id
  showSessions.value = false
  hasMore.value = true
  await loadMessages(true)
}

function startEditTitle(s: any) {
  editingSessionId.value = s.id
  editTitleInput.value = s.title
}

async function saveTitle(s: any) {
  const newTitle = editTitleInput.value.trim()
  if (newTitle && newTitle !== s.title) {
    await client.patch(`/chat/sessions/${s.id}`, { title: newTitle })
    s.title = newTitle
  }
  editingSessionId.value = null
}

function cancelEditTitle() {
  editingSessionId.value = null
}

function deleteSession(s: any, e: Event) {
  e.stopPropagation()
  // 第一次点：进入确认状态
  if (deletingSessionId.value !== s.id) {
    deletingSessionId.value = s.id
    // 3 秒后自动取消
    setTimeout(() => {
      if (deletingSessionId.value === s.id) deletingSessionId.value = null
    }, 3000)
    return
  }
  // 第二次点：确认删除
  deletingSessionId.value = null
  client.delete(`/chat/sessions/${s.id}`).then(() => {
    if (currentSessionId.value === s.id) {
      currentSessionId.value = null
      messages.value = []
    }
    loadSessions()
  })
}

async function loadTemplates() {
  const { data } = await client.get('/templates')
  templates.value = data
}

async function checkStatus() {
  const { data } = await client.get('/checkin/status')
  weekDays.value = data.week_days
  todayDone.value = data.today_done
  if (data.pending && !notifiedToday) {
    notifiedToday = true
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('今天过得怎么样？', { body: '回一句就行，我来帮你记录～' })
    }
  }
}

async function send(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || sending.value) return
  input.value = ''
  sending.value = true

  // 如果还没创建会话，发第一条消息时才创建
  if (!currentSessionId.value) {
    const { data: newSess } = await client.post('/chat/new')
    currentSessionId.value = newSess.session_id
    await loadSessions()
  }

  messages.value.push({ role: 'user', content, id: Date.now(), display: content })
  scrollBottom()
  try {
    const { data } = await client.post('/chat', { message: content, session_id: currentSessionId.value })
    const msgId = Date.now()
    messages.value.push({ role: 'assistant', content: data.reply, id: msgId, display: '' })
    // 打字机效果
    const full = data.reply
    let i = 0
    const typeInterval = setInterval(() => {
      i += 2
      const msg = messages.value.find((m) => m.id === msgId)
      if (msg) {
        msg.display = full.slice(0, i)
        scrollBottom()
      }
      if (i >= full.length) {
        clearInterval(typeInterval)
        if (msg) msg.display = full
      }
    }, 18)
    await checkStatus()
    await loadSessions()
  } finally {
    sending.value = false
  }
}

function scrollBottom() {
  setTimeout(() => {
    listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' })
  }, 30)
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(async () => {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
  await Promise.all([loadTemplates(), checkStatus(), loadSessions()])
  pollTimer = window.setInterval(checkStatus, 60000)
})

onUnmounted(() => window.clearInterval(pollTimer))
</script>

<template>
  <div class="chat-page">
    <!-- 左侧会话列表抽屉 -->
    <div v-if="showSessions" class="sessions-sidebar" @click.self="showSessions = false">
      <div class="sessions-panel">
        <div class="sessions-header">
          <span class="sessions-title">💬 历史对话</span>
          <button class="close-btn" @click="showSessions = false">✕</button>
        </div>
        <div class="sessions-list">
          <div v-if="!sessions.length" class="session-empty">暂无历史对话</div>
          <div
            v-for="s in sessions"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === currentSessionId }"
            @click="switchSession(s.id)"
          >
            <!-- 编辑状态 -->
            <div v-if="editingSessionId === s.id" class="session-edit" @click.stop>
              <input
                v-model="editTitleInput"
                class="edit-input"
                @keyup.enter="saveTitle(s)"
                @keyup.esc="cancelEditTitle"
                autofocus
              />
              <button class="edit-save" @click="saveTitle(s)">✓</button>
            </div>
            <!-- 正常状态 -->
            <template v-else>
              <div class="session-title">
                {{ s.title }}
                <span class="edit-icon" @click.stop="startEditTitle(s)">✏️</span>
                <span
                  v-if="deletingSessionId === s.id"
                  class="delete-confirm"
                  @click.stop="deleteSession(s, $event)"
                >确认删除？</span>
                <span
                  v-else
                  class="delete-icon"
                  @click.stop="deleteSession(s, $event)"
                >🗑️</span>
              </div>
              <div class="session-meta">
                <span class="session-time">{{ formatTime(s.created_at) }}</span>
                <span class="session-count">{{ s.msg_count }} 条</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-meta">
      <div class="meta-chip" :class="{ done: todayDone }">
        <span class="chip-emoji">{{ todayDone ? '✅' : '🌙' }}</span>
        {{ todayDone ? '今日已记录' : '今日还没记录哦' }}
      </div>
      <div class="meta-chip week">
        <span class="chip-emoji">📈</span>
        本周 {{ weekDays }}<span class="slash">/7</span> 天
      </div>
      <div class="meta-actions">
        <button class="new-chat-btn" @click="newChat">＋ 新对话</button>
        <button class="menu-btn" @click="showSessions = true">☰</button>
      </div>
    </div>

    <div ref="listRef" class="chat-list" @scroll="onScroll">
      <!-- 加载更多提示 -->
      <div v-if="loadingMore" class="loading-more">
        <span class="loading-dots">
          <i></i><i></i><i></i>
        </span>
        加载更早的消息…
      </div>
      <div v-if="!hasMore && messages.length" class="no-more">
        —— 已经到底啦 ——
      </div>

      <!-- 没选会话时的引导 -->
      <div v-if="!currentSessionId" class="chat-empty">
        <div class="empty-emoji">🌱</div>
        <div class="empty-text">开始一段新的成长对话吧</div>
        <div class="empty-hint">点右上角「＋ 新对话」开始，或点「☰」看历史记录</div>
      </div>

      <!-- 有会话但没消息 -->
      <div v-else-if="!messages.length" class="chat-empty">
        <div class="empty-emoji">🌸</div>
        <div class="empty-text">和我说说今天做了什么吧</div>
        <div class="empty-hint">比如「今天读了 30 页书」「明天下午 3 点健身」</div>
      </div>
      <div v-for="m in messages" :key="m.id" class="chat-row" :class="m.role">
        <div class="bubble" :class="m.role">{{ m.display || m.content }}</div>
      </div>
      <div v-if="sending" class="chat-row assistant">
        <div class="bubble assistant thinking">
          <span class="dots"><i></i><i></i><i></i></span>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <div v-if="templates.length" class="templates">
        <span
          v-for="t in templates"
          :key="t.id"
          class="template-tag"
          @click="send(t.label)"
        >✨ {{ t.label }}</span>
      </div>
      <div class="input-row">
        <el-input
          v-model="input"
          :placeholder="currentSessionId ? '记录今天 / 问进度 / 安排日程…' : '说点什么开始新对话吧…'"
          :disabled="sending"
          @keyup.enter="send()"
        />
        <button class="send-btn" :disabled="sending" @click="send()">
          {{ sending ? '…' : '发送 🚀' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px 24px 20px;
  box-sizing: border-box;
}
.chat-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid var(--border-soft);
  font-size: 12.5px;
  color: var(--text-secondary);
  font-weight: 500;
}
.meta-chip.done {
  background: #f0f9f4;
  border-color: #c8e6d5;
  color: #3d8b6a;
  font-weight: 600;
}
.chip-emoji {
  font-size: 13px;
}
.meta-chip.week .slash {
  color: #c0c0c0;
  margin: 0 1px;
}
.meta-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.menu-btn {
  padding: 7px 12px;
  border-radius: 16px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid var(--border-soft);
  background: #fff;
  color: var(--text-secondary);
}
.menu-btn:hover {
  border-color: #b8e6d0;
  background: #f0faf4;
}
.new-chat-btn {
  padding: 7px 16px;
  border-radius: 16px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  color: #8b5a3c;
}
.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 181, 197, 0.4);
}
/* 左侧会话抽屉 */
.sessions-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(180, 160, 130, 0.2);
  z-index: 100;
  animation: fade-in 0.2s ease;
  backdrop-filter: blur(2px);
}
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
.sessions-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  bottom: 16px;
  width: 300px;
  background: #fffcf7;
  border-radius: 20px;
  box-shadow: -8px 0 32px rgba(180, 160, 130, 0.15);
  display: flex;
  flex-direction: column;
  animation: slide-in-right 0.25s ease;
  overflow: hidden;
}
@keyframes slide-in-right {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.sessions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 16px;
  background: linear-gradient(135deg, #f0faf4, #fff9f2);
}
.sessions-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}
.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.12s;
}
.close-btn:hover {
  background: #fff;
  transform: rotate(90deg);
}
.sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.sessions-list::-webkit-scrollbar {
  width: 5px;
}
.sessions-list::-webkit-scrollbar-thumb {
  background: #e8e0d4;
  border-radius: 3px;
}
.session-item {
  padding: 12px 14px;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: 6px;
  border: 1px solid transparent;
}
.session-item:hover {
  background: #fff;
  border-color: var(--border-soft);
}
.session-item.active {
  background: #f0faf4;
  border-color: #c8e6d5;
}
.session-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.edit-icon {
  font-size: 11px;
  opacity: 0;
  transition: opacity 0.15s;
  cursor: pointer;
}
.delete-icon {
  font-size: 11px;
  opacity: 0;
  transition: opacity 0.15s;
  cursor: pointer;
}
.session-item:hover .edit-icon,
.session-item:hover .delete-icon {
  opacity: 0.6;
}
.delete-icon:hover {
  opacity: 1 !important;
}
.delete-confirm {
  font-size: 11px;
  color: #e07a7a;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 8px;
  background: #fef0f0;
  white-space: nowrap;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
.session-edit {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}
.edit-input {
  flex: 1;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid #c8e6d5;
  background: #fff;
  font-size: 13px;
  outline: none;
}
.edit-input:focus {
  border-color: #7bc8a4;
}
.edit-save {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  border: none;
  background: #7bc8a4;
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.session-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}
.session-time {
  font-size: 11.5px;
  color: var(--text-secondary);
  font-weight: 500;
}
.session-count {
  font-size: 11px;
  color: #c0b8ac;
}
.session-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px 16px;
  box-sizing: border-box;
}
/* 美化滚动条 */
.chat-list::-webkit-scrollbar {
  width: 6px;
}
.chat-list::-webkit-scrollbar-track {
  background: transparent;
}
.chat-list::-webkit-scrollbar-thumb {
  background: #e0d8cc;
  border-radius: 3px;
}
.chat-list::-webkit-scrollbar-thumb:hover {
  background: #c8bfb0;
}
.loading-more {
  text-align: center;
  padding: 12px;
  font-size: 12.5px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.loading-dots {
  display: inline-flex;
  gap: 4px;
}
.loading-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #c8e6d5;
  animation: bounce 1.2s infinite;
}
.loading-dots i:nth-child(2) { animation-delay: 0.15s; }
.loading-dots i:nth-child(3) { animation-delay: 0.3s; }
.no-more {
  text-align: center;
  padding: 16px;
  font-size: 12px;
  color: #c0b8ac;
}
.chat-empty {
  text-align: center;
  margin-top: 90px;
}
.empty-emoji {
  font-size: 48px;
  margin-bottom: 14px;
}
.empty-text {
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 700;
  margin-bottom: 6px;
}
.empty-hint {
  font-size: 12.5px;
  color: var(--text-secondary);
}
.chat-row {
  display: flex;
  margin-bottom: 14px;
  animation: bubble-in 0.3s ease;
}
@keyframes bubble-in {
  from { opacity: 0; transform: translateY(8px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.chat-row.user {
  justify-content: flex-end;
}
.bubble {
  max-width: 72%;
  padding: 12px 17px;
  border-radius: 20px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble.user {
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  border-bottom-right-radius: 6px;
  font-weight: 500;
}
.bubble.assistant {
  background: #fff;
  color: var(--text-primary);
  border: 1px solid var(--border-soft);
  border-bottom-left-radius: 6px;
}
.bubble.thinking {
  padding: 14px 18px;
}
.dots {
  display: inline-flex;
  gap: 5px;
}
.dots i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c8e6d5;
  animation: bounce 1.2s infinite;
}
.dots i:nth-child(2) { animation-delay: 0.15s; }
.dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-5px); opacity: 1; }
}
.chat-input-area {
  background: #fff;
  border-radius: 20px;
  padding: 14px 16px;
  border: 1px solid var(--border-soft);
}
.templates {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.template-tag {
  padding: 5px 14px;
  border-radius: 16px;
  background: #fff5eb;
  color: #c88a3d;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}
.template-tag:hover {
  background: #ffe8d0;
  transform: translateY(-1px);
}
.input-row {
  display: flex;
  gap: 10px;
  align-items: center;
}
.input-row .el-input {
  flex: 1;
}
.input-row :deep(.el-input__wrapper) {
  border-radius: 16px;
  background: #faf6f0;
  box-shadow: none;
  padding: 4px 16px;
}
.send-btn {
  padding: 10px 22px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  color: #8b5a3c;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 181, 197, 0.4);
}
.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
