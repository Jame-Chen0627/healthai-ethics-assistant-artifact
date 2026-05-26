<template>
  <div class="chat-view" :class="{ 'dev-on': devMode }">
    <ChatSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :loading="loadingSessions"
      :is-authenticated="isAuthenticated"
      :current-user="currentUser"
      @new-chat="openNewChat"
      @select="selectSession"
      @delete="deleteSession"
      @rename="renameSession"
      @logout="logout"
    />

    <main class="chat-main">
      <header class="chat-header">
        <div class="header-left">
          <span class="brand">HealthAI Ethics Assistant</span>
          <button
            class="dev-btn"
            :class="{ active: devMode }"
            :title="devMode ? 'Open Developer panel' : 'Enable Developer Mode'"
            @click="openDevPanel"
          >
            <span class="dev-btn-tag">&lt;/&gt;</span>
            <span>Dev</span>
            <span v-if="devMode" class="dev-btn-dot" aria-hidden="true"></span>
          </button>
        </div>
        <div class="header-right" v-if="activeStakeholder">
          <span class="role-pill">
            <template v-if="activeCustomPersonaName">👤 {{ activeCustomPersonaName }}</template>
            <template v-else>{{ stakeholderIcon(activeStakeholder) }} {{ stakeholderLabel(activeStakeholder) }}</template>
          </span>
        </div>
      </header>

      <div class="thread" ref="threadEl">
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-icon">💬</div>
          <h2>Welcome to HealthAI Ethics Assistant</h2>
          <p>
            A scalable, RAG-based dialogue assistant for <strong>healthcare AI ethics requirements</strong>,
            grounded in the <strong>EU AI Act</strong>, <strong>NIST AI RMF</strong>, and real-world
            practitioner findings. Adaptive topics are planned as a future extension.
          </p>
          <p v-if="!activeStakeholder" class="welcome-cta">
            Click <strong>＋ New Chat</strong> in the sidebar to pick your role and get started.
          </p>
          <button v-if="!activeStakeholder" class="primary big-cta" @click="openNewChat">
            ＋ Start a new chat
          </button>
          <div v-else class="examples">
            <p class="examples-title">Try one of these:</p>
            <button v-for="(ex, idx) in topicExamples" :key="idx" class="example-btn" @click="useExample(ex)">
              <span class="ex-tag">{{ ex.tag }}</span>
              <span class="ex-text">{{ ex.text }}</span>
            </button>
          </div>
        </div>

        <ChatMessage
          v-for="(m, idx) in messages"
          :key="idx"
          :role="m.role"
          :message="m"
          :requirement-preferences="activeRequirementPreferences"
          @requirement-action="setRequirementPreference"
        />
      </div>

      <div class="composer-wrap">
        <div v-if="attachment" class="attachment-chip">
          <span class="att-icon">📎</span>
          <span class="att-name" :title="attachment.name">{{ attachment.name }}</span>
          <span class="att-size">{{ formatBytes(attachment.size) }}</span>
          <button class="att-remove" @click="clearAttachment" title="Remove attachment">×</button>
        </div>

        <div class="composer-tools">
          <button
            class="tool-btn"
            title="Attach a text file (.txt .md .json .csv)"
            :disabled="!activeStakeholder || sending || !!attachment"
            @click="triggerFilePick"
          >＋ Attach File</button>
          <button
            class="tool-btn doc-btn"
            title="Preview accepted requirements before downloading"
            :disabled="!canGenerateDoc"
            @click="openRequirementsDocPreview"
          >Generate Requirements Doc</button>
        </div>

        <div class="composer">
          <input
            ref="fileInputEl"
            type="file"
            accept=".txt,.md,.json,.csv,text/plain,text/markdown,application/json,text/csv"
            class="hidden-file"
            @change="onFileSelected"
          />
          <textarea
            v-model="input"
            rows="1"
            ref="inputEl"
            :placeholder="composerPlaceholder"
            @keydown.enter.exact.prevent="send"
            @input="autoresize"
            :disabled="!activeStakeholder || sending"
          ></textarea>
          <button class="primary send-btn" @click="send" :disabled="!canSend">
            {{ sending ? '…' : 'Send' }}
          </button>
        </div>
        <p v-if="attachmentError" class="att-error">⚠️ {{ attachmentError }}</p>
      </div>
    </main>

    <NewChatModal v-if="showNewChat" @cancel="showNewChat = false" @confirm="onNewChatConfirm" />
    <DevPanel v-if="showDevPanel" :enabled="devMode" :last-debug="lastDebug" :last-result="lastResult" @close="showDevPanel = false" @toggle="setDevMode" />
    <ConfirmModal
      v-if="confirmDialog"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-label="confirmDialog.confirmLabel"
      :cancel-label="confirmDialog.cancelLabel"
      :tone="confirmDialog.tone"
      @confirm="onConfirmYes"
      @cancel="onConfirmNo"
    />

    <div v-if="docPreviewOpen" class="doc-preview-backdrop" @click.self="closeDocPreview">
      <section class="doc-preview-modal" role="dialog" aria-modal="true" aria-label="Requirements document preview">
        <header class="doc-preview-header">
          <div>
            <div class="doc-kicker">Requirements Document</div>
            <h3>{{ docPreview?.title || 'Accepted Requirements' }}</h3>
          </div>
          <button class="doc-close" type="button" aria-label="Close preview" @click="closeDocPreview">×</button>
        </header>
        <div class="doc-preview-body">
          <a v-if="docPreview?.chat_url" class="doc-chat-link" :href="docPreview.chat_url" target="_blank" rel="noreferrer">
            Open this chat
          </a>
          <div class="doc-meta">
            <div><span>Chat</span><p>{{ docPreview?.chat_prompt }}</p></div>
            <div><span>Topic</span><p>{{ docPreview?.topic }}</p></div>
            <div><span>Persona</span><p>{{ docPreview?.persona }}</p></div>
            <div v-if="docPreview?.project_context"><span>Project context</span><p>{{ docPreview.project_context }}</p></div>
          </div>
          <div v-if="!docPreview?.accepted_count" class="doc-empty">No accepted requirements selected yet.</div>
          <div v-for="group in docPreview?.groups || []" :key="group.dimension" class="doc-group">
            <h4>{{ group.dimension }}</h4>
            <article v-for="(item, idx) in group.items" :key="item.requirement_key || idx" class="doc-req">
              <strong>{{ idx + 1 }}. {{ item.title || 'Requirement' }}</strong>
              <p v-if="item.description">{{ item.description }}</p>
              <p>{{ item.requirement_text }}</p>
              <small v-if="item.guideline_refs?.length">
                {{ formatDocRefs(item.guideline_refs) }}
              </small>
            </article>
          </div>
        </div>
        <footer class="doc-preview-actions">
          <button class="tool-btn" type="button" @click="closeDocPreview">Cancel</button>
          <button class="tool-btn doc-btn" type="button" @click="downloadPreviewedRequirementsDoc">Download .docx</button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ChatSidebar from '../components/ChatSidebar.vue'
import ChatMessage from '../components/ChatMessage.vue'
import NewChatModal from '../components/NewChatModal.vue'
import DevPanel from '../components/DevPanel.vue'
import ConfirmModal from '../components/ConfirmModal.vue'
import {
  ethicsChat,
  listChatSessions,
  createChatSession,
  getChatSession,
  deleteChatSession,
  renameChatSession,
  listRequirementPreferences,
  saveRequirementPreference,
  getRequirementsDocPreview,
  downloadRequirementsDoc,
  getMe,
} from '../api/index.js'
import {
  isGuestSessionId,
  listGuestSessions,
  getGuestSession,
  createGuestSession,
  deleteGuestSession,
  updateGuestSession,
  listGuestRequirementPreferences,
  upsertGuestRequirementPreference,
  appendGuestMessage,
} from '../utils/guestSessions.js'

const router = useRouter()
const route = useRoute()

const STAKEHOLDER_LABELS = {
  HCP: 'Healthcare Professional',
  SEng: 'Software Engineer',
  HCR: 'Healthcare Researcher',
}
const STAKEHOLDER_ICONS = { HCP: '🩺', SEng: '💻', HCR: '🔬' }
function stakeholderLabel(s) { return STAKEHOLDER_LABELS[s] || s }
function stakeholderIcon(s) { return STAKEHOLDER_ICONS[s] || '💬' }

const HEALTHAI_EXAMPLES = [
  { tag: 'Create',   text: 'I am building a CT-scan triage AI. What privacy requirements should I include?' },
  { tag: 'Validate', text: 'Validate this requirement: "Only authorised radiologists may access patient scans."' },
  { tag: 'Compare',  text: 'Compare this with practice: "Store patient CT scans in an encrypted database."' },
]

const TOPIC_EXAMPLES = [
  {
    match: /cybersecurity/i,
    examples: [
      { tag: 'Create', text: 'I am building an account recovery flow for a SaaS platform. What security requirements should I include?' },
      { tag: 'Validate', text: 'Validate this requirement: "Admins must use MFA before changing user permissions."' },
      { tag: 'Compare', text: 'Compare this with practice: "All privileged actions must be logged and reviewed weekly."' },
    ],
  },
  {
    match: /mobile|ux|heuristic/i,
    examples: [
      { tag: 'Create', text: 'I am designing a mobile checkout flow. What usability and accessibility requirements should I include?' },
      { tag: 'Validate', text: 'Validate this requirement: "Primary actions must be reachable with one thumb on common phone sizes."' },
      { tag: 'Compare', text: 'Compare this with practice: "Error messages must explain what went wrong and how to recover."' },
    ],
  },
  {
    match: /education|curriculum/i,
    examples: [
      { tag: 'Create', text: 'I am designing an online assessment module. What curriculum and learning requirements should I include?' },
      { tag: 'Validate', text: 'Validate this requirement: "Each quiz question must map to a measurable learning outcome."' },
      { tag: 'Compare', text: 'Compare this with practice: "Learners must receive feedback after each formative assessment."' },
    ],
  },
  {
    match: /smart[-\s]?home|iot/i,
    examples: [
      { tag: 'Create', text: 'I am building a smart-home hub. What privacy and device-control requirements should I include?' },
      { tag: 'Validate', text: 'Validate this requirement: "Only authorised household members may remotely unlock connected smart locks."' },
      { tag: 'Compare', text: 'Compare this with practice: "The hub must let users review and delete voice command history."' },
    ],
  },
]

// ── Auth state ────────────────────────────────────────────────────
const currentUser = ref(null)
const isAuthenticated = computed(() => !!currentUser.value)

// ── Developer Mode (auth-gated) ───────────────────────────────────
const devMode = ref(localStorage.getItem('dev_mode') === '1')
const showDevPanel = ref(false)
const lastDebug = ref(null) // { capturedAt, prompt, stakeholder, mode, calls: [...] }
const lastResult = ref(null) // { mode, create|validate|compare } — latest assistant response payload

// Read Developer-Mode overrides + RAG docs from localStorage on each send.
// They're written by DevPanel; both are JSON, both optional.
function readDevOverrides() {
  if (!devMode.value) return {}
  const out = {}
  try {
    const raw = localStorage.getItem('dev_overrides_v1')
    if (raw) {
      const o = JSON.parse(raw)
      if (o && typeof o === 'object') {
        if (o.model) out.model_override = String(o.model).trim()
        if (o.temperature !== '' && o.temperature != null) out.temperature_override = Number(o.temperature)
        if (o.max_tokens !== '' && o.max_tokens != null) out.max_tokens_override = Number(o.max_tokens)
      }
    }
  } catch { /* ignore */ }
  try {
    const rawDocs = localStorage.getItem('dev_rag_v1')
    if (rawDocs) {
      const docs = JSON.parse(rawDocs)
      if (Array.isArray(docs) && docs.length) {
        out.rag_docs = docs
          .filter((d) => d && d.content)
          .map((d) => ({ name: d.name || 'untitled', content: d.content }))
      }
    }
  } catch { /* ignore */ }
  return out
}

function setDevMode(on) {
  devMode.value = !!on
  if (on) localStorage.setItem('dev_mode', '1')
  else localStorage.removeItem('dev_mode')
}

// ── Custom confirm modal (replaces window.confirm) ───────────────────
const confirmDialog = ref(null) // { title, message, confirmLabel, cancelLabel, tone, resolve }
const docPreviewOpen = ref(false)
const docPreview = ref(null)
function askConfirm(opts) {
  return new Promise((resolve) => {
    confirmDialog.value = { ...opts, resolve }
  })
}
function onConfirmYes() {
  const d = confirmDialog.value
  confirmDialog.value = null
  d?.resolve?.(true)
}
function onConfirmNo() {
  const d = confirmDialog.value
  confirmDialog.value = null
  d?.resolve?.(false)
}

async function openDevPanel() {
  if (!isAuthenticated.value) {
    const go = await askConfirm({
      title: 'Sign in required',
      message: 'Developer Mode is only available to logged-in users. Sign in now?',
      confirmLabel: 'Sign in',
      cancelLabel: 'Not now',
    })
    if (go) router.push('/login')
    return
  }
  if (!devMode.value) setDevMode(true)
  showDevPanel.value = true
}

async function refreshMe() {
  const token = localStorage.getItem('access_token')
  if (!token) { currentUser.value = null; return }
  try {
    currentUser.value = await getMe()
  } catch (e) {
    currentUser.value = null
    localStorage.removeItem('access_token')
  }
}

async function logout() {
  const ok = await askConfirm({
    title: 'Sign out',
    message: 'Sign out of your account? Your guest sessions will remain in this browser.',
    confirmLabel: 'Sign out',
    cancelLabel: 'Stay signed in',
  })
  if (!ok) return
  localStorage.removeItem('access_token')
  currentUser.value = null
  sessions.value = []
  setDevMode(false)
  showDevPanel.value = false
  resetChat()
  // Stay on the assistant view in guest mode instead of bouncing to /login.
  await refreshSessions()
}

// ── Sessions ──────────────────────────────────────────────────────
const sessions = ref([])
const loadingSessions = ref(false)
const activeSessionId = ref(null)
const activeStakeholder = ref(null)
const activeSystemContext = ref(null)
const activeCustomPersona = ref(null)
const activeCustomPersonaName = ref(null)
const activeTopic = ref(null)
const activeTopicPrompt = ref(null)
const activeRequirementPreferences = ref([])

const topicExamples = computed(() => {
  const label = activeTopic.value || 'HealthAI Ethics'
  if (/healthai|healthcare|medical|ethics/i.test(label)) return HEALTHAI_EXAMPLES
  const matched = TOPIC_EXAMPLES.find((group) => group.match.test(label))
  if (matched) return matched.examples
  const topicName = label.trim() || 'this topic'
  return [
    { tag: 'Create', text: `I am working on ${topicName}. What requirements should I include?` },
    { tag: 'Validate', text: `Validate this requirement for ${topicName}: "Only authorised users may access sensitive records and controls."` },
    { tag: 'Compare', text: `Compare this with practice for ${topicName}: "The system must log important user actions and support review."` },
  ]
})

async function refreshSessions() {
  if (!isAuthenticated.value) {
    sessions.value = listGuestSessions()
    return
  }
  loadingSessions.value = true
  try {
    sessions.value = await listChatSessions()
  } catch (e) {
    sessions.value = []
  } finally {
    loadingSessions.value = false
  }
}

async function selectSession(id) {
  if (id === activeSessionId.value) return
  // Guest session: load from sessionStorage
  if (isGuestSessionId(id)) {
    const detail = getGuestSession(id)
    if (!detail) return
    activeSessionId.value = detail.id
    activeStakeholder.value = detail.stakeholder || 'SEng'
    activeSystemContext.value = detail.system_context || null
    activeCustomPersona.value = detail.custom_persona || null
    activeCustomPersonaName.value = detail.custom_persona_name || null
    activeTopic.value = detail.topic || null
    activeTopicPrompt.value = detail.topic_prompt || null
    activeRequirementPreferences.value = listGuestRequirementPreferences(detail.id)
    messages.value = detail.messages.map(deserializeStoredMessage).filter(Boolean)
    router.replace({ name: 'home' }).catch(() => {})
    scrollToBottom()
    return
  }
  try {
    const detail = await getChatSession(id)
    activeSessionId.value = detail.id
    activeStakeholder.value = detail.stakeholder || 'SEng'
    messages.value = detail.messages.map(deserializeStoredMessage).filter(Boolean)
    activeSystemContext.value = detail.system_context || null
    activeCustomPersona.value = detail.custom_persona || null
    activeCustomPersonaName.value = detail.custom_persona_name || null
    activeTopic.value = detail.topic || null
    activeTopicPrompt.value = detail.topic_prompt || null
    activeRequirementPreferences.value = await listRequirementPreferences(detail.id)
    router.replace({ name: 'home', query: { session: String(detail.id) } }).catch(() => {})
    scrollToBottom()
  } catch (e) {
    console.error(e)
  }
}

function deserializeStoredMessage(m) {
  if (m.role === 'user') {
    return { role: 'user', content: m.content }
  }
  // assistant content is JSON of the chat response
  try {
    const parsed = JSON.parse(m.content)
    return {
      role: 'assistant',
      mode: parsed.mode,
      assistant_text: parsed.assistant_text || '',
      create: parsed.create,
      validate: parsed.validate,
      compare: parsed.compare,
      message_id: parsed.message_id,
    }
  } catch {
    return { role: 'assistant', mode: null, assistant_text: m.content }
  }
}

async function deleteSession(id) {
  const ok = await askConfirm({
    title: 'Delete chat',
    message: 'This conversation will be permanently removed. Continue?',
    confirmLabel: 'Delete',
    cancelLabel: 'Cancel',
    tone: 'danger',
  })
  if (!ok) return
  if (isGuestSessionId(id)) {
    deleteGuestSession(id)
    if (activeSessionId.value === id) resetChat()
    await refreshSessions()
    return
  }
  try {
    await deleteChatSession(id)
    if (activeSessionId.value === id) resetChat()
    await refreshSessions()
  } catch (e) {
    console.error(e)
  }
}

async function renameSession({ id, title, topic }) {
  if (!title) return
  const patch = topic === undefined ? { title } : { title, topic }
  if (isGuestSessionId(id)) {
    updateGuestSession(id, patch)
    if (activeSessionId.value === id && topic !== undefined) activeTopic.value = topic || null
    if (activeSessionId.value === id) activeRequirementPreferences.value = listGuestRequirementPreferences(id)
    await refreshSessions()
    return
  }
  try {
    await renameChatSession(id, patch)
    if (activeSessionId.value === id && topic !== undefined) activeTopic.value = topic || null
    if (activeSessionId.value === id) activeRequirementPreferences.value = await listRequirementPreferences(id)
    await refreshSessions()
  } catch (e) {
    console.error(e)
  }
}

function resetChat() {
  activeSessionId.value = null
  activeStakeholder.value = null
  activeSystemContext.value = null
  activeCustomPersona.value = null
  activeCustomPersonaName.value = null
  activeTopic.value = null
  activeTopicPrompt.value = null
  activeRequirementPreferences.value = []
  docPreviewOpen.value = false
  docPreview.value = null
  messages.value = []
  input.value = ''
  activeRequirementPreferences.value = []
  clearAttachment()
}

// ── New chat flow ─────────────────────────────────────────────────
const showNewChat = ref(false)
function openNewChat() { showNewChat.value = true }

async function onNewChatConfirm({ stakeholder, systemContext, customPersona, customPersonaName, topic, topicPrompt, chatName }) {
  showNewChat.value = false
  activeStakeholder.value = stakeholder
  activeSystemContext.value = systemContext
  activeCustomPersona.value = customPersona || null
  activeCustomPersonaName.value = customPersonaName || null
  activeTopic.value = topic || null
  activeTopicPrompt.value = topicPrompt || null
  messages.value = []
  input.value = ''

  const titleForSession = (chatName && chatName.trim()) || 'New Chat'

  if (isAuthenticated.value) {
    try {
      const sess = await createChatSession({
        title: titleForSession,
        mode: 'chat',
        stakeholder,
        topic: topic || null,
        topic_prompt: topicPrompt || null,
        system_context: systemContext || null,
        custom_persona: customPersona || null,
        custom_persona_name: customPersonaName || null,
      })
      activeSessionId.value = sess.id
      activeRequirementPreferences.value = await listRequirementPreferences(sess.id)
      await refreshSessions()
    } catch (e) {
      console.error(e)
    }
  } else {
    const sess = createGuestSession({
      title: titleForSession,
      stakeholder,
      system_context: systemContext || null,
      custom_persona: customPersona || null,
      custom_persona_name: customPersonaName || null,
      topic: topic || null,
      topic_prompt: topicPrompt || null,
    })
    activeSessionId.value = sess.id
    activeRequirementPreferences.value = []
    await refreshSessions()
  }
}

// ── Messaging ─────────────────────────────────────────────────────
const messages = ref([])
const input = ref('')
const sending = ref(false)
const threadEl = ref(null)
const inputEl = ref(null)

// ── Attachment ────────────────────────────────────────
const MAX_ATTACHMENT_BYTES = 200 * 1024 // 200 KB
const ALLOWED_EXT = ['txt', 'md', 'json', 'csv']
const attachment = ref(null)        // { name, size, content }
const attachmentError = ref('')
const fileInputEl = ref(null)

function triggerFilePick() {
  attachmentError.value = ''
  fileInputEl.value?.click()
}

function clearAttachment() {
  attachment.value = null
  attachmentError.value = ''
  if (fileInputEl.value) fileInputEl.value.value = ''
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  attachmentError.value = ''

  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED_EXT.includes(ext)) {
    attachmentError.value = `Unsupported file type ".${ext}". Allowed: ${ALLOWED_EXT.map(e => '.' + e).join(', ')}.`
    e.target.value = ''
    return
  }
  if (file.size > MAX_ATTACHMENT_BYTES) {
    attachmentError.value = `File is too large (${formatBytes(file.size)}). Max ${formatBytes(MAX_ATTACHMENT_BYTES)}.`
    e.target.value = ''
    return
  }

  try {
    const content = await file.text()
    attachment.value = { name: file.name, size: file.size, content }
  } catch (err) {
    attachmentError.value = `Could not read file: ${err.message || err}`
  } finally {
    // allow re-selecting the same file later after removing
    e.target.value = ''
  }
}

const composerPlaceholder = computed(() => {
  if (!activeStakeholder.value) return 'Click ＋ New Chat in the sidebar to start…'
  if (attachment.value) return 'Add a question or instruction about the attached file…'
  return 'Type your message — I will pick the right mode (Create / Validate / Compare).'
})

const canSend = computed(() => {
  if (!activeStakeholder.value || sending.value) return false
  return input.value.trim().length > 0 || !!attachment.value
})

const canGenerateDoc = computed(() => (
  isAuthenticated.value
  && typeof activeSessionId.value === 'number'
  && activeRequirementPreferences.value.some((p) => p.status === 'accepted')
))

function autoresize() {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

function useExample(ex) {
  input.value = ex.text
  nextTick(autoresize)
}

function scrollToBottom() {
  nextTick(() => {
    const el = threadEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function send() {
  if (!canSend.value) return
  const userText = input.value.trim()
  const att = attachment.value

  // What the user sees in their bubble
  const bubbleContent = att
    ? (userText
        ? `📎 ${att.name}\n\n${userText}`
        : `📎 ${att.name} — (please analyse this file)`)
    : userText

  // What we send to the LLM
  const promptForLLM = att
    ? `[Attached file: ${att.name} (${formatBytes(att.size)})]\n"""\n${att.content}\n"""\n\n${userText || 'Please analyse the attached file in the most appropriate mode (create / validate / compare).'}`
    : userText

  input.value = ''
  clearAttachment()
  autoresize()

  messages.value.push({ role: 'user', content: bubbleContent })
  const placeholderIdx = messages.value.length
  messages.value.push({ role: 'assistant', pending: true })
  scrollToBottom()
  sending.value = true

  // Persist user message immediately for guest sessions
  const guestId = isGuestSessionId(activeSessionId.value) ? activeSessionId.value : null
  if (guestId) {
    appendGuestMessage(guestId, { role: 'user', content: bubbleContent })
    await refreshSessions()
  }

  try {
    const devExtras = readDevOverrides()
    const guestSuppressed = isGuestSessionId(activeSessionId.value)
      ? activeRequirementPreferences.value.filter((p) => p.status === 'suppressed')
      : []
    const res = await ethicsChat({
      prompt: promptForLLM,
      stakeholder: activeStakeholder.value,
      // Only forward numeric backend IDs; guest ids are local-only.
      session_id: typeof activeSessionId.value === 'number' ? activeSessionId.value : undefined,
      system_context: activeSystemContext.value || undefined,
      custom_persona: activeCustomPersona.value || undefined,
      topic: activeTopic.value || undefined,
      topic_prompt: activeTopicPrompt.value || undefined,
      suppressed_requirements: guestSuppressed.length ? guestSuppressed : undefined,
      debug: devMode.value || undefined,
      ...devExtras,
    })
    if (devMode.value && Array.isArray(res.debug)) {
      lastDebug.value = {
        capturedAt: new Date().toISOString(),
        prompt: promptForLLM,
        stakeholder: activeStakeholder.value,
        mode: res.mode,
        calls: res.debug,
      }
    }
    if (devMode.value) {
      lastResult.value = {
        mode: res.mode,
        create: res.create,
        validate: res.validate,
        compare: res.compare,
      }
    }
    messages.value[placeholderIdx] = {
      role: 'assistant',
      pending: false,
      mode: res.mode,
      assistant_text: res.assistant_text || '',
      create: res.create,
      validate: res.validate,
      compare: res.compare,
      message_id: res.message_id,
    }
    if (guestId) {
      // Store assistant content as JSON string to mirror server schema
      const stored = JSON.stringify({
        mode: res.mode,
        assistant_text: res.assistant_text || '',
        create: res.create,
        validate: res.validate,
        compare: res.compare,
        message_id: res.message_id,
      })
      appendGuestMessage(guestId, { role: 'assistant', content: stored })
      await refreshSessions()
    }
    if (isAuthenticated.value) await refreshSessions()
  } catch (e) {
    messages.value[placeholderIdx] = {
      role: 'assistant',
      pending: false,
      error: e.response?.data?.detail || e.message || 'Request failed.',
    }
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

async function setRequirementPreference(pref) {
  if (!activeSessionId.value || !pref?.requirement_text) return
  try {
    if (isGuestSessionId(activeSessionId.value)) {
      upsertGuestRequirementPreference(activeSessionId.value, pref)
      activeRequirementPreferences.value = listGuestRequirementPreferences(activeSessionId.value)
      await refreshSessions()
      return
    }
    if (typeof activeSessionId.value !== 'number') return
    await saveRequirementPreference(activeSessionId.value, pref)
    activeRequirementPreferences.value = await listRequirementPreferences(activeSessionId.value)
  } catch (e) {
    console.error(e)
  }
}

function activeChatUrl() {
  if (typeof activeSessionId.value !== 'number') return window.location.href
  const url = new URL(window.location.href)
  url.searchParams.set('session', String(activeSessionId.value))
  return url.toString()
}

function formatDocRefs(refs = []) {
  return refs.map((r) => (
    `${r.framework || ''} ${r.article || ''}${r.title ? ` (${r.title})` : ''}`
  ).trim()).filter(Boolean).join('; ')
}

async function openRequirementsDocPreview() {
  if (!canGenerateDoc.value) return
  try {
    docPreview.value = await getRequirementsDocPreview(activeSessionId.value, activeChatUrl())
    docPreviewOpen.value = true
  } catch (e) {
    console.error(e)
  }
}

function closeDocPreview() {
  docPreviewOpen.value = false
}

async function downloadPreviewedRequirementsDoc() {
  if (!canGenerateDoc.value) return
  try {
    const blob = await downloadRequirementsDoc(activeSessionId.value, activeChatUrl())
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const name = (activeTopic.value || 'requirements').replace(/[^a-z0-9._-]+/gi, '_')
    a.href = url
    a.download = `${name || 'requirements'}.docx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  await refreshMe()
  await refreshSessions()
  const sessionFromUrl = Number(route.query.session)
  if (isAuthenticated.value && Number.isFinite(sessionFromUrl) && sessionFromUrl > 0) {
    await selectSession(sessionFromUrl)
  }
  // Dev Mode requires auth; clear any stale toggle from previous logged-in session.
  if (!isAuthenticated.value && devMode.value) {
    setDevMode(false)
    showDevPanel.value = false
  }
})
</script>

<style scoped>
.chat-view {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--color-bg);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}
.brand {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-left {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.header-right { flex-shrink: 0; }
.dev-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.dev-btn:hover { border-color: var(--color-accent); color: var(--color-text); }
.dev-btn.active {
  border-color: #fb8500;
  color: #b15a00;
  background: #fff4e5;
}
.dev-btn-tag {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
}
.dev-btn-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #fb8500;
}

.dev-on .chat-header {
  box-shadow: inset 0 -2px 0 0 #fb8500;
}

.role-pill {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
}

.thread {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  scroll-behavior: smooth;
}

.welcome {
  max-width: 720px;
  margin: 40px auto;
  text-align: center;
}
.welcome-icon { font-size: 48px; margin-bottom: 8px; }
.welcome h2 { margin: 0 0 8px; font-size: 20px; }
.welcome p { color: var(--color-text-muted); font-size: 14px; line-height: 1.6; margin: 6px 0; }
.welcome-cta { margin-top: 16px; color: var(--color-text); }
.big-cta {
  margin-top: 12px;
  font-size: 15px;
  padding: 10px 20px;
}
.examples {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: stretch;
  text-align: left;
}
.examples-title { color: var(--color-text-muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0; }
.example-btn {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 10px 14px;
  cursor: pointer;
  text-align: left;
  font-size: 13px;
  transition: border-color 0.15s, background 0.15s;
}
.example-btn:hover { border-color: var(--color-accent); background: #f6f8fa; }
.ex-tag {
  background: var(--color-surface-2);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-muted);
  flex-shrink: 0;
}
.ex-text { line-height: 1.4; }

.composer-wrap {
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  padding: 12px 24px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attachment-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px 8px 4px 12px;
  font-size: 12px;
  max-width: 100%;
}
.att-icon { font-size: 14px; }
.att-name {
  font-weight: 600;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.att-size { color: var(--color-text-muted); font-size: 11px; }
.att-remove {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-size: 16px;
  line-height: 1;
  width: 22px; height: 22px;
  border-radius: 50%;
  cursor: pointer;
  padding: 0;
}
.att-remove:hover { background: #ffebe9; color: var(--color-error); }
.att-error {
  margin: 0;
  font-size: 12px;
  color: var(--color-error);
}
.hidden-file { display: none; }

.composer-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.tool-btn {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
}
.tool-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.tool-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.doc-btn {
  background: #dafbe1;
  border-color: #4ac26b66;
  color: var(--color-success);
}

.doc-preview-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1250;
  background: rgba(15, 20, 28, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.doc-preview-modal {
  width: min(760px, 94vw);
  max-height: 88vh;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: 0 22px 60px rgba(31, 35, 40, 0.24);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.doc-preview-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--color-border);
}
.doc-kicker {
  color: var(--color-success);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.doc-preview-header h3 {
  margin: 3px 0 0;
  font-size: 18px;
}
.doc-close {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 24px;
  line-height: 1;
}
.doc-close:hover { background: var(--color-surface-2); color: var(--color-text); }
.doc-preview-body {
  overflow-y: auto;
  padding: 16px 18px;
}
.doc-chat-link {
  display: inline-flex;
  margin-bottom: 12px;
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}
.doc-chat-link:hover { text-decoration: underline; }
.doc-meta {
  display: grid;
  gap: 10px;
  margin-bottom: 16px;
}
.doc-meta div {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
}
.doc-meta span {
  color: var(--color-text-muted);
  display: block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.4px;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.doc-meta p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.doc-group {
  margin-top: 16px;
}
.doc-group h4 {
  margin: 0 0 8px;
  color: var(--color-create);
  font-size: 15px;
}
.doc-req {
  border-left: 3px solid var(--color-create);
  padding: 8px 0 10px 12px;
  margin-bottom: 10px;
}
.doc-req strong { display: block; margin-bottom: 5px; }
.doc-req p {
  margin: 5px 0;
  font-size: 13px;
  line-height: 1.5;
}
.doc-req small {
  color: var(--color-text-muted);
  display: block;
  font-size: 12px;
  line-height: 1.4;
}
.doc-empty {
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 10px 0;
}
.doc-preview-actions {
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 18px;
}

.composer {
  display: flex;
  align-items: center;
  gap: 8px;
}
.composer textarea {
  flex: 1;
  resize: none;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.4;
  min-height: 40px;
  max-height: 180px;
  outline: none;
  background: var(--color-surface);
}
.composer textarea:focus { border-color: var(--color-accent); }
.composer textarea:disabled { background: var(--color-surface-2); cursor: not-allowed; }

.send-btn {
  flex-shrink: 0;
  height: 38px;
  min-width: 72px;
}

@media (max-width: 760px) {
  .thread { padding: 16px; }
  .composer-wrap { padding: 10px 12px 14px; }
}
</style>
