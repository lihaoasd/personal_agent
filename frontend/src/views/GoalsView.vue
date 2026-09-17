<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'
import Confetti from '../components/Confetti.vue'

const goals = ref<any[]>([])
const activeTab = ref('all')
const loading = ref(false)
const confettiTrigger = ref(0)
const selectedGoalId = ref<number | null>(null)

const selectedGoal = computed(() => goals.value.find((g) => g.id === selectedGoalId.value) || null)

const wizardVisible = ref(false)
const wizardDesc = ref('')
const wizardReason = ref('')
const wizardCategory = ref('learning')
const wizardLoading = ref(false)
const plan = ref<any>(null)

const simpleVisible = ref(false)
const simpleTitle = ref('')
const simpleReason = ref('')
const simpleCategory = ref('general')

const editGoalVisible = ref(false)
const editGoalForm = ref({ id: 0, title: '', category: 'general', status: 'active', reason: '' })
const editingGoalId = ref<number | null>(null)
const editTaskId = ref<number | null>(null)
const editTaskText = ref('')
const newTaskTitle = ref('')
const showNewTaskInput = ref(false)

const categoryLabels: Record<string, string> = { general: '通用', learning: '学习', health: '健康', habit: '习惯' }
const categoryEmoji: Record<string, string> = { general: '📌', learning: '📚', health: '💪', habit: '🔄' }
const categoryColors: Record<string, string> = {
  general: '#7bc8a4', learning: '#7bc8a4', health: '#7bc8a4', habit: '#7bc8a4',
}
const statusTypes: Record<string, string> = { active: 'success', paused: 'info', done: 'warning', abandoned: 'danger' }
const statusLabels: Record<string, string> = { active: '进行中', paused: '暂停', done: '已完成', abandoned: '已放弃' }
const itemTypeLabels: Record<string, string> = { task: '任务', course: '课程', book: '书籍', practice: '实践' }

async function load() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (activeTab.value !== 'all') params.category = activeTab.value
    const { data } = await client.get('/goals', { params })
    goals.value = data
    // 默认选中第一个
    if (!selectedGoalId.value && data.length) {
      selectedGoalId.value = data[0].id
    }
    // 如果选中的目标不在列表里，重新选第一个
    if (selectedGoalId.value && !data.find((g: any) => g.id === selectedGoalId.value)) {
      selectedGoalId.value = data.length ? data[0].id : null
    }
  } finally {
    loading.value = false
  }
}

async function runPlan() {
  if (!wizardDesc.value.trim()) return
  wizardLoading.value = true
  plan.value = null
  try {
    const { data } = await client.post('/goals/plan', {
      description: wizardDesc.value,
      category: wizardCategory.value,
    })
    plan.value = data
  } finally {
    wizardLoading.value = false
  }
}

async function confirmPlan() {
  if (!wizardDesc.value.trim()) return
  const { data } = await client.post('/goals/from-plan', {
    description: wizardDesc.value,
    category: wizardCategory.value,
    reason: wizardReason.value,
  })
  ElMessage.success(`已创建目标「${data.title}」🎉`)
  wizardVisible.value = false
  wizardDesc.value = ''
  wizardReason.value = ''
  plan.value = null
  await load()
}

async function createSimple() {
  if (!simpleTitle.value.trim()) return
  await client.post('/goals', {
    title: simpleTitle.value,
    reason: simpleReason.value,
    category: simpleCategory.value,
  })
  ElMessage.success('已创建目标 ✨')
  simpleVisible.value = false
  simpleTitle.value = ''
  simpleReason.value = ''
  await load()
}

async function toggleTask(task: any) {
  const wasDone = task.status === 'done'
  await client.patch(`/goals/tasks/${task.id}`, { status: wasDone ? 'todo' : 'done' })
  if (!wasDone) confettiTrigger.value++
  await load()

  if (selectedGoal.value && selectedGoal.value.tasks.length > 0) {
    const allDone = selectedGoal.value.tasks.every((t: any) => t.status === 'done')
    // 全部完成 → 自动标记为已完成
    if (!wasDone && allDone && selectedGoal.value.status === 'active') {
      await client.patch(`/goals/${selectedGoal.value.id}`, { status: 'done' })
      confettiTrigger.value += 5
      ElMessage.success('🎉 恭喜！目标全部完成啦！')
      await load()
    }
    // 取消了一个已完成任务 → 从已完成改回进行中
    if (wasDone && selectedGoal.value.status === 'done') {
      await client.patch(`/goals/${selectedGoal.value.id}`, { status: 'active' })
      ElMessage.info('已改回进行中 🌱')
      await load()
    }
  }
}

async function aiDecompose(goal: any) {
  const { data } = await client.post('/goals/plan', { description: goal.title, category: goal.category })
  if (!data.tasks?.length) {
    ElMessage.info('AI 觉得这个目标无需再拆解～')
    return
  }
  for (const t of data.tasks) {
    await client.post(`/goals/${goal.id}/tasks`, { title: t.title, item_type: t.item_type })
  }
  ElMessage.success(`已拆解 ${data.tasks.length} 条子任务 🎯`)
  await load()
}

async function confirmDelete(goal: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除目标「${goal.title}」吗？该目标下的所有子任务会一起删除。`,
      '删除目标',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await client.delete(`/goals/${goal.id}`)
    ElMessage.success('已删除 🗑️')
    await load()
  } catch {
    // 用户取消
  }
}

function openEditGoal(goal: any) {
  editGoalForm.value = {
    id: goal.id,
    title: goal.title,
    category: goal.category,
    status: goal.status,
    reason: goal.reason || '',
  }
  editingGoalId.value = goal.id
}

async function saveEditGoal() {
  if (!editGoalForm.value.title.trim()) return
  await client.patch(`/goals/${editGoalForm.value.id}`, {
    title: editGoalForm.value.title,
    reason: editGoalForm.value.reason,
    category: editGoalForm.value.category,
    status: editGoalForm.value.status,
  })
  ElMessage.success('已保存 ✨')
  editingGoalId.value = null
  await load()
}

function cancelEditGoal() {
  editingGoalId.value = null
}

function startEditTask(task: any) {
  editTaskId.value = task.id
  editTaskText.value = task.title
}

async function saveEditTask() {
  if (!editTaskText.value.trim() || editTaskId.value === null) return
  await client.patch(`/goals/tasks/${editTaskId.value}`, { title: editTaskText.value })
  ElMessage.success('已保存 ✨')
  editTaskId.value = null
  await load()
}

function cancelEditTask() {
  editTaskId.value = null
}

async function addTaskInline() {
  if (!newTaskTitle.value.trim() || !selectedGoal.value) return
  await client.post(`/goals/${selectedGoal.value.id}/tasks`, { title: newTaskTitle.value })
  ElMessage.success('已添加 ✨')
  newTaskTitle.value = ''
  showNewTaskInput.value = false
  await load()
}

async function deleteTask(task: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除子任务「${task.title}」吗？`,
      '删除任务',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await client.delete(`/goals/tasks/${task.id}`)
    ElMessage.success('已删除 🗑️')
    await load()
  } catch {
    // 用户取消
  }
}

async function confirmAbandon() {
  if (!selectedGoal.value) return
  try {
    await ElMessageBox.confirm(
      `确定放弃目标「${selectedGoal.value.title}」吗？放弃不是失败，只是这个阶段不太合适～`,
      '放弃目标',
      { confirmButtonText: '放弃', cancelButtonText: '再想想', type: 'warning' },
    )
    await client.patch(`/goals/${selectedGoal.value.id}`, { status: 'abandoned' })
    ElMessage.success('已标记为放弃 💔 没关系的')
    await load()
  } catch {
    // 用户取消
  }
}

async function reactivateGoal() {
  if (!selectedGoal.value) return
  await client.patch(`/goals/${selectedGoal.value.id}`, { status: 'active' })
  ElMessage.success('重新出发！🌱')
  await load()
}

async function addTask() {
  if (!addTaskTitle.value.trim() || !selectedGoal.value) return
  await client.post(`/goals/${selectedGoal.value.id}/tasks`, { title: addTaskTitle.value })
  ElMessage.success('已添加 ✨')
  addTaskVisible.value = false
  addTaskTitle.value = ''
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">目标计划 🎯</h2>
        <div class="page-subtitle">AI 帮你把大目标拆成可执行的小步骤</div>
      </div>
      <div class="head-actions">
        <button class="btn-primary" @click="wizardVisible = true">✨ AI 设定目标</button>
        <button class="btn-ghost" @click="simpleVisible = true">＋ 简单创建</button>
      </div>
    </div>

    <div class="tabs">
      <span
        v-for="t in [{ k: 'all', l: '全部 🌟' }, { k: 'learning', l: '学习 📚' }, { k: 'health', l: '健康 💪' }, { k: 'habit', l: '习惯 🔄' }]"
        :key="t.k"
        class="tab"
        :class="{ active: activeTab === t.k }"
        @click="activeTab = t.k; load()"
      >{{ t.l }}</span>
    </div>

    <div v-loading="loading" class="goal-layout">
      <!-- 左栏：目标列表 -->
      <div class="goal-sidebar">
        <div v-if="!goals.length" class="empty-state small">
          <div class="empty-emoji">🌱</div>
          <div>还没有目标</div>
        </div>
        <div
          v-for="g in goals"
          :key="g.id"
          class="goal-item"
          :class="{ active: selectedGoalId === g.id }"
          @click="selectedGoalId = g.id"
        >
          <div class="goal-item-head">
            <span class="goal-emoji">{{ categoryEmoji[g.category] }}</span>
            <span class="goal-item-title">{{ g.title }}</span>
          </div>
          <div class="goal-item-progress">
            <div class="mini-progress-bar">
              <div class="mini-progress-fill" :style="{ width: g.progress.total_tasks ? (g.progress.done_tasks / g.progress.total_tasks * 100) + '%' : '0%', background: categoryColors[g.category] }"></div>
            </div>
            <span class="mini-progress-text">{{ g.progress.done_tasks }}/{{ g.progress.total_tasks }}</span>
          </div>
        </div>
      </div>

      <!-- 右栏：目标详情 -->
      <div class="goal-detail">
        <div v-if="!selectedGoal" class="empty-state">
          <div class="empty-emoji">🎯</div>
          <div>选择一个目标查看详情</div>
        </div>

        <div v-else class="goal-card detail-card">
          <div class="goal-body">
            <div class="goal-head">
              <!-- 编辑模式：显示输入框 -->
              <div v-if="editingGoalId === selectedGoal.id" class="edit-mode-area">
                <div class="edit-label">✏️ 编辑目标</div>
                <el-input v-model="editGoalForm.title" size="default" placeholder="目标名称" />
                <div class="edit-reason">
                  <label>💫 我的初衷</label>
                  <el-input
                    v-model="editGoalForm.reason"
                    type="textarea"
                    :rows="2"
                    placeholder="写下你为什么要做这个目标"
                  />
                </div>
                <div class="edit-meta-row">
                  <div class="edit-field">
                    <span class="edit-field-label">分类</span>
                    <select v-model="editGoalForm.category" class="mini-select">
                      <option value="general">📌 通用</option>
                      <option value="learning">📚 学习</option>
                      <option value="health">💪 健康</option>
                      <option value="habit">🔄 习惯</option>
                    </select>
                  </div>
                  <div class="edit-field">
                    <span class="edit-field-label">状态</span>
                    <select v-model="editGoalForm.status" class="mini-select">
                      <option value="active">🌱 进行中</option>
                      <option value="paused">⏸️ 暂停</option>
                      <option value="done">🎉 已完成</option>
                      <option value="abandoned">💔 已放弃</option>
                    </select>
                  </div>
                </div>
              </div>
              <!-- 只读模式 -->
              <div v-else class="goal-title-row">
                <span class="goal-emoji big">{{ categoryEmoji[selectedGoal.category] }}</span>
                <span class="goal-title big">{{ selectedGoal.title }}</span>
                <el-tag size="small" :type="statusTypes[selectedGoal.status]" effect="light" round>{{ statusLabels[selectedGoal.status] }}</el-tag>
              </div>
              <div class="head-btns">
                <template v-if="editingGoalId === selectedGoal.id">
                  <button class="save-btn" @click="saveEditGoal">✅ 保存</button>
                  <button class="cancel-btn" @click="cancelEditGoal">取消</button>
                </template>
                <template v-else>
                  <button class="decompose-btn" @click="openEditGoal(selectedGoal)">✏️ 编辑</button>
                  <button class="decompose-btn" @click="aiDecompose(selectedGoal)">✨ AI 拆解</button>
                  <button v-if="selectedGoal.status !== 'abandoned'" class="abandon-btn" @click="confirmAbandon">💔 放弃</button>
                  <button v-if="selectedGoal.status === 'abandoned'" class="reactivate-btn" @click="reactivateGoal">🌱 重新开始</button>
                  <button class="delete-btn" @click="confirmDelete(selectedGoal)">🗑️</button>
                </template>
              </div>
            </div>

            <div class="progress-area">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: selectedGoal.progress.total_tasks ? (selectedGoal.progress.done_tasks / selectedGoal.progress.total_tasks * 100) + '%' : '0%', background: categoryColors[selectedGoal.category] }"></div>
              </div>
              <span class="progress-text">{{ selectedGoal.progress.done_tasks }}/{{ selectedGoal.progress.total_tasks }} 已完成</span>
            </div>

            <div v-if="selectedGoal.reason" class="reason-card">
              <div class="reason-label">💫 我的初衷</div>
              <div class="reason-text">{{ selectedGoal.reason }}</div>
            </div>

            <div class="task-list">
              <div class="task-list-head">📋 步骤（{{ selectedGoal.tasks.length }}）</div>
              <div v-for="t in selectedGoal.tasks" :key="t.id" class="task-row">
                <template v-if="editTaskId === t.id">
                  <span class="checkbox" :class="{ checked: t.status === 'done' }">
                    <span v-if="t.status === 'done'">✓</span>
                  </span>
                  <el-input v-model="editTaskText" size="small" autofocus @keyup.enter="saveEditTask" @keyup.esc="cancelEditTask" />
                  <button class="task-edit-btn" @click="saveEditTask">✅</button>
                  <button class="task-del-btn" @click="cancelEditTask">✕</button>
                </template>
                <template v-else>
                  <span class="checkbox" :class="{ checked: t.status === 'done' }" @click.stop="toggleTask(t)">
                    <span v-if="t.status === 'done'">✓</span>
                  </span>
                  <span :class="{ done: t.status === 'done' }" class="task-title" @click="toggleTask(t)">{{ t.title }}</span>
                  <span class="task-type">{{ itemTypeLabels[t.item_type] }}</span>
                  <template v-if="editingGoalId === selectedGoal.id">
                    <button class="task-edit-btn" @click.stop="startEditTask(t)">✏️</button>
                    <button class="task-del-btn" @click.stop="deleteTask(t)">✕</button>
                  </template>
                </template>
              </div>
              <div v-if="!selectedGoal.tasks.length && !showNewTaskInput" class="task-empty">
                暂无子任务，点「✨ AI 拆解」或下面的按钮添加吧～
              </div>
              <div v-if="showNewTaskInput && editingGoalId === selectedGoal.id" class="task-row new-task-row">
                <span class="checkbox"></span>
                <el-input v-model="newTaskTitle" size="small" placeholder="输入新任务，回车确认" autofocus @keyup.enter="addTaskInline" @keyup.esc="showNewTaskInput = false" />
                <button class="task-edit-btn" @click="addTaskInline">✅</button>
              </div>
              <button v-if="!showNewTaskInput && editingGoalId === selectedGoal.id" class="add-task-btn" @click="showNewTaskInput = true">＋ 添加子任务</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="wizardVisible" title="✨ AI 设定目标" width="540px" class="cute-dialog">
      <div class="form-group">
        <label>🎯 你想做什么？</label>
        <el-input
          v-model="wizardDesc"
          type="textarea"
          :rows="3"
          placeholder="用一句话描述你的目标，例如：9 月完成系统设计学习并读完 2 本书"
        />
      </div>
      <div class="form-group">
        <label>💫 为什么设立这个目标？</label>
        <el-input
          v-model="wizardReason"
          type="textarea"
          :rows="2"
          placeholder="写下你的初衷，迷茫的时候回来看看～"
        />
      </div>
      <div class="cat-picker">
        <span
          v-for="c in [{ k: 'learning', l: '📚 学习' }, { k: 'health', l: '💪 健康' }, { k: 'habit', l: '🔄 习惯' }, { k: 'general', l: '📌 通用' }]"
          :key="c.k"
          class="cat-option"
          :class="{ active: wizardCategory === c.k }"
          @click="wizardCategory = c.k"
        >{{ c.l }}</span>
      </div>
      <button class="btn-primary" :disabled="wizardLoading" @click="runPlan">
        {{ wizardLoading ? '思考中…' : 'AI 拆解 ✨' }}
      </button>

      <div v-if="plan" class="plan-preview">
        <div class="plan-title">🎯 {{ plan.title }}</div>
        <div v-for="(t, i) in plan.tasks" :key="i" class="plan-task">
          <span class="plan-num">{{ i + 1 }}</span>
          <span>{{ t.title }}</span>
          <el-tag size="small" effect="plain" round>{{ itemTypeLabels[t.item_type] }}</el-tag>
        </div>
        <el-alert v-if="!plan.tasks?.length" type="info" :closable="false"
                  title="AI 认为该目标无需拆解，确认后将仅创建目标" />
      </div>

      <template #footer>
        <el-button @click="wizardVisible = false">取消</el-button>
        <button class="btn-primary" :disabled="!plan" @click="confirmPlan">确认创建 🎉</button>
      </template>
    </el-dialog>

    <el-dialog v-model="simpleVisible" title="简单创建目标" width="460px" class="cute-dialog">
      <div class="form-group">
        <label>目标名称</label>
        <el-input v-model="simpleTitle" placeholder="目标名称，如：每天运动 30 分钟" />
      </div>
      <div class="form-group">
        <label>💫 为什么设立这个目标？</label>
        <el-input
          v-model="simpleReason"
          type="textarea"
          :rows="2"
          placeholder="写下你的初衷，迷茫的时候回来看看～"
        />
      </div>
      <div class="cat-picker">
        <span
          v-for="c in [{ k: 'learning', l: '📚 学习' }, { k: 'health', l: '💪 健康' }, { k: 'habit', l: '🔄 习惯' }, { k: 'general', l: '📌 通用' }]"
          :key="c.k"
          class="cat-option"
          :class="{ active: simpleCategory === c.k }"
          @click="simpleCategory = c.k"
        >{{ c.l }}</span>
      </div>
      <template #footer>
        <el-button @click="simpleVisible = false">取消</el-button>
        <button class="btn-primary" @click="createSimple">创建 ✨</button>
      </template>
    </el-dialog>

    <Confetti :trigger="confettiTrigger" />
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
.btn-primary {
  padding: 9px 20px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 200, 164, 0.35);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-ghost {
  padding: 9px 18px;
  border-radius: 16px;
  border: 1.5px solid var(--border-soft);
  background: #fff;
  color: var(--text-primary);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-ghost:hover {
  border-color: #d4c5f0;
  background: #faf8ff;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.tab {
  padding: 7px 18px;
  border-radius: 18px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
  border: 1px solid var(--border-soft);
  font-weight: 500;
}
.tab.active {
  background: linear-gradient(135deg, #b8e6d0, #d4f0e2);
  color: #3d8b6a;
  border-color: transparent;
  font-weight: 700;
}
.goal-layout {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}
.goal-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding-right: 4px;
}
.goal-item {
  background: #fff;
  border-radius: 16px;
  border: 1.5px solid var(--border-soft);
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s;
}
.goal-item:hover {
  border-color: #e0d8cc;
  transform: translateY(-1px);
}
.goal-item.active {
  border-color: #7bc8a4;
  background: linear-gradient(135deg, #f0faf4, #fff);
  box-shadow: 0 2px 12px rgba(123, 200, 164, 0.15);
}
.goal-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.goal-item-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.goal-item-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mini-progress-bar {
  flex: 1;
  height: 6px;
  background: #f5f0e8;
  border-radius: 4px;
  overflow: hidden;
}
.mini-progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.mini-progress-text {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
}
.goal-detail {
  flex: 1;
  min-width: 0;
}
.detail-card {
  background: #fff;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-soft);
  overflow: hidden;
}
.detail-card.editing {
  background: linear-gradient(180deg, #f0faf4 0%, #fff 100%);
  border-color: #b8e6d0;
  box-shadow: 0 4px 20px rgba(123, 200, 164, 0.12);
}
.goal-emoji.big {
  font-size: 26px;
}
.goal-title.big {
  font-size: 18px;
}
.task-list-head {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
  padding-left: 2px;
}
.empty-state.small {
  padding: 30px 10px;
  font-size: 13px;
}
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
  font-size: 14px;
}
.empty-emoji {
  font-size: 48px;
  margin-bottom: 12px;
}
.goal-card {
  background: #fff;
  border-radius: var(--radius-card);
  border: 1px solid var(--border-soft);
  overflow: hidden;
  transition: transform 0.15s, box-shadow 0.15s;
}
.goal-card.editing {
  background: linear-gradient(180deg, #f0faf4 0%, #fff 100%);
  border-color: #b8e6d0;
  box-shadow: 0 4px 20px rgba(123, 200, 164, 0.12);
}
.goal-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(180, 160, 130, 0.1);
}
.goal-card.editing:hover {
  transform: none;
  box-shadow: 0 4px 20px rgba(123, 200, 164, 0.12);
}
.goal-body {
  padding: 18px 20px;
}
.goal-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
}
.goal-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.goal-emoji {
  font-size: 20px;
}
.goal-title {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text-primary);
}
.decompose-btn {
  padding: 5px 14px;
  border-radius: 14px;
  border: none;
  background: #faf8ff;
  color: #8b7ab8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.decompose-btn:hover {
  background: #f0ecfa;
}
.head-btns {
  display: flex;
  gap: 6px;
  align-items: center;
}
.delete-btn {
  padding: 5px 10px;
  border-radius: 14px;
  border: none;
  background: #fff0f3;
  color: #c06878;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.delete-btn:hover {
  background: #ffe0e6;
  transform: scale(1.05);
}
.abandon-btn {
  padding: 5px 12px;
  border-radius: 14px;
  border: none;
  background: #f5f0f5;
  color: #9a7ba8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.abandon-btn:hover {
  background: #ece0f0;
}
.reactivate-btn {
  padding: 5px 12px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.reactivate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(123, 200, 164, 0.35);
}
.delete-btn:hover {
  background: #ffe0e6;
  transform: scale(1.05);
}
.progress-area {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.progress-bar {
  flex: 1;
  height: 10px;
  background: #f5f0e8;
  border-radius: 6px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.4s ease;
}
.progress-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 700;
  flex-shrink: 0;
}
.reason-card {
  background: linear-gradient(135deg, #fef3e0, #fff8ed);
  border: 1.5px solid #f5e0b8;
  border-radius: 18px;
  padding: 16px 18px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}
.reason-card::before {
  content: '✨';
  position: absolute;
  top: 8px;
  right: 12px;
  font-size: 16px;
  opacity: 0.5;
}
.reason-label {
  font-size: 12px;
  font-weight: 700;
  color: #c49048;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}
.reason-text {
  font-size: 13.5px;
  color: #8a6a38;
  line-height: 1.7;
  font-style: italic;
}
.task-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.12s;
}
.task-row:hover {
  background: #faf6f0;
}
.checkbox {
  width: 20px;
  height: 20px;
  border-radius: 8px;
  border: 2px solid #e0d8cc;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}
.checkbox.checked {
  background: #7bc8a4;
  border-color: #7bc8a4;
}
.task-title {
  flex: 1;
  font-size: 13.5px;
  color: var(--text-primary);
}
.task-title.done {
  text-decoration: line-through;
  color: #c0c0c0;
}
.task-type {
  font-size: 11px;
  color: var(--text-secondary);
  background: #f5f0e8;
  padding: 2px 9px;
  border-radius: 10px;
}
.task-empty {
  font-size: 12.5px;
  color: #c0c0c0;
  padding: 8px 10px;
}
.add-task-btn {
  width: 100%;
  padding: 10px;
  border-radius: 14px;
  border: 1.5px dashed #e0d8cc;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  margin-top: 8px;
}
.add-task-btn:hover {
  border-color: #b8e6d0;
  background: #f0faf4;
  color: #3d8b6a;
}
.new-task-row {
  background: #f0faf4;
  border-radius: 12px;
  padding: 8px 10px;
}
.new-task-row :deep(.el-input__wrapper) {
  border-radius: 10px !important;
  box-shadow: 0 0 0 1.5px #b8e6d0 inset !important;
}
.task-edit-btn,
.task-del-btn {
  padding: 3px 9px;
  border-radius: 10px;
  border: none;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.task-edit-btn:hover {
  background: #f0ecfa;
  transform: scale(1.08);
}
.task-del-btn:hover {
  background: #fff0f3;
  color: #c06878;
  transform: scale(1.08);
}
.form-group {
  margin-bottom: 18px;
}
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.form-group :deep(.el-textarea__inner),
.form-group :deep(.el-input__wrapper) {
  border-radius: 14px !important;
  box-shadow: 0 0 0 1.5px #f0e8dc inset !important;
  background: #fffdf9 !important;
  transition: box-shadow 0.15s;
}
.form-group :deep(.el-textarea__inner):focus,
.form-group :deep(.el-input__wrapper):focus-within {
  box-shadow: 0 0 0 2px #b8e6d0 inset !important;
}
.edit-mode-area {
  flex: 1;
  min-width: 0;
}
.edit-label {
  font-size: 12px;
  font-weight: 700;
  color: #3d8b6a;
  margin-bottom: 8px;
}
.edit-mode-area :deep(.el-input__wrapper) {
  border-radius: 14px !important;
  box-shadow: 0 0 0 1.5px #b8e6d0 inset !important;
  background: #fff !important;
}
.edit-reason {
  margin-top: 10px;
}
.edit-reason label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.edit-meta-row {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.edit-field {
  display: flex;
  align-items: center;
  gap: 8px;
}
.edit-field-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}
.mini-select {
  padding: 6px 12px;
  border-radius: 12px;
  border: 1.5px solid #d4ead9;
  background: #fff;
  font-size: 12.5px;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}
.mini-select:hover {
  border-color: #7bc8a4;
}
.save-btn {
  padding: 7px 16px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 200, 164, 0.4);
}
.cancel-btn {
  padding: 7px 14px;
  border-radius: 14px;
  border: 1.5px solid #e8e2d8;
  background: #fff;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.cancel-btn:hover {
  background: #f5f0e8;
  border-color: #d8d0c4;
}
.cute-dialog :deep(.el-dialog) {
  border-radius: 24px !important;
  border: 1px solid var(--border-soft);
  box-shadow: 0 16px 48px rgba(180, 160, 130, 0.2);
}
.cute-dialog :deep(.el-dialog__header) {
  padding: 20px 24px 12px !important;
  margin: 0 !important;
  border-bottom: 1px solid #faf5ee;
}
.cute-dialog :deep(.el-dialog__title) {
  font-weight: 700 !important;
  font-size: 16px !important;
}
.cute-dialog :deep(.el-dialog__body) {
  padding: 20px 24px !important;
}
.cute-dialog :deep(.el-dialog__footer) {
  padding: 12px 24px 20px !important;
  border-top: 1px solid #faf5ee;
}
.cat-picker {
  display: flex;
  gap: 8px;
  margin: 14px 0;
  flex-wrap: wrap;
}
.cat-option {
  padding: 7px 16px;
  border-radius: 14px;
  background: #f5f0e8;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}
.cat-option.active {
  background: #f0f9f4;
  color: #3d8b6a;
  font-weight: 700;
}
.plan-preview {
  margin-top: 14px;
  background: #faf8f3;
  border-radius: 16px;
  padding: 16px 18px;
}
.plan-title {
  font-weight: 700;
  margin-bottom: 10px;
  color: var(--text-primary);
  font-size: 15px;
}
.plan-task {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-size: 13px;
}
.plan-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>
