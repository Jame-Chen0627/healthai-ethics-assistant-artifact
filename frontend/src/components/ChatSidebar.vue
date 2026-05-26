<template>
  <aside class="sidebar">
    <button class="new-chat-btn" @click="$emit('new-chat')">
      <span class="plus">＋</span> New Chat
    </button>

    <div v-if="!isAuthenticated" class="login-hint">
      <p>You're chatting as a guest. Sessions are kept only in this tab.</p>
      <router-link to="/login" class="login-link">Log in to save chat history →</router-link>
    </div>

    <h3 class="history-title">Chat Sessions</h3>
    <div v-if="loading" class="muted">Loading…</div>
    <div v-else-if="!sessions.length" class="muted">No sessions yet.</div>
    <ul v-else class="session-list">
      <li
        v-for="s in sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === activeSessionId }"
        @click="editingId === s.id ? null : $emit('select', s.id)"
      >
        <div class="session-row">
          <span class="session-icon">{{ sessionIcon(s) }}</span>
          <div class="session-meta">
            <template v-if="editingId === s.id">
              <label class="edit-label" @click.stop>
                <span>Note</span>
                <input
                  ref="editInputEl"
                  v-model="editingTitle"
                  class="edit-input"
                  maxlength="80"
                  @click.stop
                  @keydown.enter.prevent="commitEdit(s)"
                  @keydown.escape.prevent="cancelEdit"
                />
              </label>
              <div class="edit-actions" @click.stop>
                <button type="button" class="mini-btn save" @click="commitEdit(s)">Save</button>
                <button type="button" class="mini-btn" @click="cancelEdit">Cancel</button>
              </div>
            </template>
            <template v-else>
              <div class="session-topic" :title="s.topic || 'General'">
                {{ s.topic || 'General' }}
              </div>
              <div class="session-title" :title="s.title">{{ s.title || 'Untitled' }}</div>
              <div class="session-sub">{{ formatDate(s.updated_at) }}</div>
            </template>
          </div>
          <button
            v-if="editingId !== s.id"
            class="icon-action edit-btn"
            title="Edit note"
            @click.stop="startEdit(s)"
          >✎</button>
          <button
            v-if="editingId !== s.id"
            class="icon-action del-btn"
            title="Delete session"
            @click.stop="$emit('delete', s.id)"
          >×</button>
        </div>
      </li>
    </ul>

    <div class="sidebar-footer">
      <div v-if="isAuthenticated && currentUser" class="user-info">
        <span class="avatar">{{ avatarInitial(currentUser.username) }}</span>
        <span class="username">{{ currentUser.username }}</span>
        <button class="logout-btn" @click="$emit('logout')">Log out</button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, nextTick } from 'vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: [Number, String, null], default: null },
  loading: { type: Boolean, default: false },
  isAuthenticated: { type: Boolean, default: false },
  currentUser: { type: Object, default: null },
})

const emit = defineEmits(['new-chat', 'select', 'delete', 'logout', 'rename'])

const editingId = ref(null)
const editingTitle = ref('')
const editInputEl = ref(null)

function startEdit(s) {
  editingId.value = s.id
  editingTitle.value = s.title || ''
  nextTick(() => {
    const el = Array.isArray(editInputEl.value) ? editInputEl.value[0] : editInputEl.value
    if (el) {
      el.focus()
      el.select()
    }
  })
}

function cancelEdit() {
  editingId.value = null
  editingTitle.value = ''
}

function commitEdit(s) {
  if (editingId.value !== s.id) return
  const next = (editingTitle.value || '').trim()
  const prev = s.title || ''
  editingId.value = null
  editingTitle.value = ''
  if (next && next !== prev) {
    emit('rename', { id: s.id, title: next || prev || 'New Chat' })
  }
}

const STAKEHOLDER_ICONS = { HCP: '🩺', SEng: '💻', HCR: '🔬' }
function sessionIcon(s) {
  return s.custom_persona_name ? '👤' : stakeholderIcon(s.stakeholder)
}
function stakeholderIcon(s) {
  return STAKEHOLDER_ICONS[s] || '💬'
}
function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  // Always render in Melbourne local time so users see consistent timestamps.
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Australia/Melbourne',
  })
}
function avatarInitial(name) {
  return (name || '?').trim().charAt(0).toUpperCase()
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--color-surface-2);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  gap: 12px;
  overflow: hidden;
}

.new-chat-btn {
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.new-chat-btn:hover { filter: brightness(1.05); }
.plus { font-size: 16px; line-height: 1; }

.login-hint {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px;
  font-size: 13px;
  color: var(--color-text-muted);
}
.login-link { color: var(--color-accent); font-weight: 600; text-decoration: none; }
.login-link:hover { text-decoration: underline; }

.history-title {
  margin: 8px 4px 4px;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
  text-transform: none;
  letter-spacing: 0;
}

.muted {
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 8px 4px;
}

.session-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.session-item {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 8px 10px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.session-item:hover { background: #f6f8fa; }
.session-item.active {
  border-color: var(--color-accent);
  background: #ddf4ff;
}

.session-row { display: flex; align-items: center; gap: 8px; }
.session-icon { font-size: 16px; }
.session-meta { flex: 1; min-width: 0; }
.session-topic {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}
.session-title {
  font-size: 11.5px;
  font-weight: 500;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}
.session-sub {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}
.del-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
  border-radius: 4px;
}
.del-btn:hover { background: #ffebe9; color: var(--color-error); }

.icon-action {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  line-height: 1;
}
.edit-btn { font-size: 13px; }
.edit-btn:hover { background: var(--color-surface-2); color: var(--color-accent); }

.edit-input {
  width: 100%;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 6px;
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  background: #fff;
  color: var(--color-text);
  outline: none;
  box-sizing: border-box;
}
.edit-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 5px;
}
.edit-label span {
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.edit-actions {
  display: flex;
  gap: 6px;
}
.mini-btn {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  border-radius: 5px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
}
.mini-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.mini-btn.save {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: #fff;
}

.sidebar-footer {
  border-top: 1px solid var(--color-border);
  padding-top: 10px;
  margin-top: auto;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--color-accent);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
}
.username { flex: 1; font-weight: 600; }
.logout-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
}
.logout-btn:hover { color: var(--color-error); border-color: var(--color-error); }
</style>
