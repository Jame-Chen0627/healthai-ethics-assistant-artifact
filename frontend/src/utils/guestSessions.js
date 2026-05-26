// Guest chat sessions stored in sessionStorage so they live only for the
// current browser tab. Cleared automatically when the tab is closed.
//
// Shape mirrors the authenticated session API enough for the sidebar /
// view to treat both uniformly.

const STORAGE_KEY = 'guest_chat_sessions_v1'

function _read() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function _write(list) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    /* sessionStorage full or unavailable — silently ignore */
  }
}

function _nowIso() {
  return new Date().toISOString()
}

export function isGuestSessionId(id) {
  return typeof id === 'string' && id.startsWith('guest-')
}

export function listGuestSessions() {
  // Return newest first to match server behaviour.
  return _read().sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))
}

export function getGuestSession(id) {
  return _read().find((s) => s.id === id) || null
}

export function createGuestSession({ title = 'New Chat', stakeholder = null, system_context = null, custom_persona = null, custom_persona_name = null, topic = null, topic_prompt = null } = {}) {
  const list = _read()
  const now = _nowIso()
  const session = {
    id: `guest-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    title,
    stakeholder,
    system_context,
    custom_persona,
    custom_persona_name,
    topic,
    topic_prompt,
    requirement_preferences: [],
    messages: [],
    created_at: now,
    updated_at: now,
  }
  list.push(session)
  _write(list)
  return session
}

function _reqKey(text) {
  return (text || '').trim().toLowerCase().replace(/\s+/g, ' ')
}

export function listGuestRequirementPreferences(id) {
  const sess = getGuestSession(id)
  return sess?.requirement_preferences || []
}

export function upsertGuestRequirementPreference(id, pref) {
  const list = _read()
  const idx = list.findIndex((s) => s.id === id)
  if (idx === -1) return null
  const prefs = Array.isArray(list[idx].requirement_preferences)
    ? list[idx].requirement_preferences
    : []
  const key = _reqKey(pref.requirement_text)
  const existingIdx = prefs.findIndex((p) => p.requirement_key === key)
  const now = _nowIso()
  const next = {
    ...pref,
    id: existingIdx >= 0 ? prefs[existingIdx].id : `guest-pref-${Date.now()}`,
    session_id: id,
    requirement_key: key,
    created_at: existingIdx >= 0 ? prefs[existingIdx].created_at : now,
    updated_at: now,
  }
  if (existingIdx >= 0) prefs[existingIdx] = next
  else prefs.push(next)
  list[idx].requirement_preferences = prefs
  list[idx].updated_at = now
  _write(list)
  return next
}

export function deleteGuestSession(id) {
  _write(_read().filter((s) => s.id !== id))
}

export function renameGuestSession(id, title) {
  return updateGuestSession(id, { title })
}

export function updateGuestSession(id, patch = {}) {
  const list = _read()
  const idx = list.findIndex((s) => s.id === id)
  if (idx === -1) return null
  if (patch.title != null) list[idx].title = patch.title
  if (patch.topic !== undefined) list[idx].topic = patch.topic
  if (patch.topic_prompt !== undefined) list[idx].topic_prompt = patch.topic_prompt
  list[idx].updated_at = _nowIso()
  _write(list)
  return list[idx]
}

export function appendGuestMessage(id, message) {
  const list = _read()
  const idx = list.findIndex((s) => s.id === id)
  if (idx === -1) return null
  list[idx].messages.push(message)
  list[idx].updated_at = _nowIso()
  // Auto-title from first user message if still default.
  if ((list[idx].title === 'New Chat' || !list[idx].title) && message.role === 'user') {
    const text = (message.content || '').trim().replace(/\s+/g, ' ')
    if (text) list[idx].title = text.length > 40 ? text.slice(0, 40) + '…' : text
  }
  _write(list)
  return list[idx]
}
