import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Auth ────────────────────────────────────────────────────────

export async function register(payload) {
  const { data } = await api.post('/auth/register', payload)
  return data
}

export async function login(payload) {
  const { data } = await api.post('/auth/login', payload)
  return data
}

export async function getMe() {
  const { data } = await api.get('/auth/me')
  return data
}

// ── Ethics knowledge base ───────────────────────────────────────

export async function listFrameworks() {
  const { data } = await api.get('/ethics/frameworks')
  return data
}

export async function listFrameworkNames() {
  const { data } = await api.get('/ethics/framework-names')
  return data.frameworks || []
}

export async function listFindings(params = {}) {
  const { data } = await api.get('/ethics/findings', { params })
  return data
}

// ── Ethics modes ─────────────────────────────────────────────────

export async function createRequirements(payload) {
  const { data } = await api.post('/ethics/create', payload)
  return data
}

export async function validateRequirements(payload) {
  const { data } = await api.post('/ethics/validate', payload)
  return data
}

export async function compareScenarios(payload) {
  const { data } = await api.post('/ethics/compare', payload)
  return data
}

export async function ethicsChat(payload) {
  const { data } = await api.post('/ethics/chat', payload)
  return data
}

// ── Chat sessions (free-form fallback, auth required) ──────────

export async function listChatSessions() {
  const { data } = await api.get('/chat/sessions')
  return data
}

export async function createChatSession(payload = {}) {
  const { data } = await api.post('/chat/sessions', payload)
  return data
}

export async function getChatSession(id) {
  const { data } = await api.get(`/chat/sessions/${id}`)
  return data
}

export async function deleteChatSession(id) {
  await api.delete(`/chat/sessions/${id}`)
}

export async function renameChatSession(id, titleOrPayload) {
  const payload = typeof titleOrPayload === 'object' ? titleOrPayload : { title: titleOrPayload }
  const { data } = await api.patch(`/chat/sessions/${id}`, payload)
  return data
}

export async function listRequirementPreferences(sessionId) {
  const { data } = await api.get(`/chat/sessions/${sessionId}/requirements`)
  return data
}

export async function saveRequirementPreference(sessionId, payload) {
  const { data } = await api.post(`/chat/sessions/${sessionId}/requirements`, payload)
  return data
}

export async function getRequirementsDocPreview(sessionId, chatUrl) {
  const { data } = await api.get(`/chat/sessions/${sessionId}/requirements-doc-preview`, {
    params: chatUrl ? { chat_url: chatUrl } : undefined,
  })
  return data
}

export async function downloadRequirementsDoc(sessionId, chatUrl) {
  const { data } = await api.get(`/chat/sessions/${sessionId}/requirements-doc`, {
    responseType: 'blob',
    params: chatUrl ? { chat_url: chatUrl } : undefined,
  })
  return data
}
