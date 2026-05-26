<template>
  <div class="dev-backdrop" @click.self="$emit('close')">
    <aside class="dev-panel" role="dialog" aria-label="Developer panel">
      <header class="dev-header">
        <div class="dev-title">
          <span class="dev-badge">&lt;/&gt;</span>
          <span>Developer Mode</span>
        </div>
        <button class="dev-close" @click="$emit('close')" aria-label="Close">×</button>
      </header>

      <div class="dev-toggle-row">
        <label class="switch">
          <input type="checkbox" :checked="enabled" @change="$emit('toggle', $event.target.checked)" />
          <span class="slider" />
        </label>
        <div>
          <div class="toggle-label">Dev Mode {{ enabled ? 'enabled' : 'disabled' }}</div>
          <div class="toggle-hint">
            When on, every chat request asks the API to return its full prompt + raw Gemini
            response so you can inspect them below. State is stored locally in your browser.
          </div>
        </div>
      </div>

      <div class="dev-main">
        <nav class="dev-rail" aria-label="Developer tools">
          <button
            v-for="item in tabs"
            :key="item.id"
            :class="{ active: tab === item.id }"
            :title="item.label"
            :aria-label="item.label"
            @click="tab = item.id"
          >
            <span class="rail-icon" v-html="item.icon" />
            <span class="rail-label">{{ item.short }}</span>
          </button>
        </nav>

        <section class="dev-body">
        <div class="section-title">{{ activeTab.label }}</div>
        <!-- ── No data yet ─────────────────────────────────────────── -->
        <div v-if="(tab === 'prompt' || tab === 'raw') && !lastDebug" class="empty">
          <p>No request captured yet.</p>
          <p class="hint">
            Make sure Dev Mode is enabled, then send a chat message. The Prompt Inspector and
            Raw Response Viewer will populate with the latest exchange.
          </p>
        </div>

        <!-- ── Prompt Inspector ────────────────────────────────────── -->
        <div v-else-if="tab === 'prompt' && lastDebug" class="content">
          <div class="meta-grid">
            <div><span class="k">Captured</span><span>{{ formatTime(lastDebug.capturedAt) }}</span></div>
            <div><span class="k">Stakeholder</span><span>{{ lastDebug.stakeholder }}</span></div>
            <div><span class="k">Mode</span><span class="badge">{{ lastDebug.mode }}</span></div>
            <div><span class="k">LLM calls</span><span>{{ lastDebug.calls.length }}</span></div>
          </div>

          <div class="user-prompt">
            <h4>User prompt</h4>
            <pre>{{ lastDebug.prompt }}</pre>
          </div>

          <div v-for="(call, i) in lastDebug.calls" :key="`p-${i}`" class="call">
            <div class="call-header">
              <span class="call-num">#{{ i + 1 }}</span>
              <span class="model">{{ call.model }}</span>
              <span class="cfg">temp {{ call.generation_config?.temperature ?? '–' }} ·
                max {{ call.generation_config?.maxOutputTokens ?? '–' }}</span>
            </div>
            <details open>
              <summary>System prompt ({{ (call.system_prompt || '').length }} chars)</summary>
              <pre>{{ call.system_prompt }}</pre>
            </details>
            <details>
              <summary>User content ({{ (call.user_content || '').length }} chars)</summary>
              <pre>{{ call.user_content }}</pre>
            </details>
          </div>
        </div>

        <!-- ── Raw Response Viewer ─────────────────────────────────── -->
        <div v-else-if="tab === 'raw' && lastDebug" class="content">
          <div class="meta-grid">
            <div><span class="k">Captured</span><span>{{ formatTime(lastDebug.capturedAt) }}</span></div>
            <div><span class="k">LLM calls</span><span>{{ lastDebug.calls.length }}</span></div>
            <div><span class="k">Total prompt tokens</span><span>{{ totalUsage.prompt }}</span></div>
            <div><span class="k">Total output tokens</span><span>{{ totalUsage.output }}</span></div>
          </div>

          <div v-for="(call, i) in lastDebug.calls" :key="`r-${i}`" class="call">
            <div class="call-header">
              <span class="call-num">#{{ i + 1 }}</span>
              <span class="model">{{ call.model }}</span>
              <span class="finish" :class="finishClass(call.finish_reason)">
                {{ call.finish_reason || 'STOP' }}
              </span>
            </div>
            <div v-if="call.usage" class="usage-row">
              <span>prompt: {{ call.usage.promptTokenCount ?? 0 }}</span>
              <span>output: {{ call.usage.candidatesTokenCount ?? 0 }}</span>
              <span>total: {{ call.usage.totalTokenCount ?? 0 }}</span>
            </div>
            <details open>
              <summary>Decoded text ({{ (call.text || '').length }} chars)</summary>
              <pre>{{ call.text }}</pre>
            </details>
            <details>
              <summary>Raw Gemini JSON</summary>
              <pre>{{ pretty(call.raw_response) }}</pre>
            </details>
            <button class="copy-btn" @click="copy(call.raw_response)">
              {{ copied === i ? 'Copied!' : 'Copy raw JSON' }}
            </button>
          </div>
        </div>

        <!-- ── Model & Params Switcher ─────────────────────── -->
        <div v-else-if="tab === 'params'" class="content">
          <p class="hint">
            Override the Gemini model name, sampling temperature and max output tokens for
            <strong>every</strong> chat request while Dev Mode is on. Stored locally in your browser.
          </p>
          <label class="field">
            <span>Model</span>
            <input
              v-model.trim="overrides.model"
              type="text"
              :placeholder="`default: ${defaultModel}`"
              @change="saveOverrides"
            />
            <small>e.g. <code>gemini-2.5-flash</code>, <code>gemini-2.5-pro</code>. Blank = backend default.</small>
          </label>
          <label class="field">
            <span>Temperature <em>{{ overrides.temperature === '' ? 'default' : overrides.temperature }}</em></span>
            <div class="row">
              <input
                type="range" min="0" max="2" step="0.1"
                :value="overrides.temperature === '' ? 0.4 : overrides.temperature"
                @input="overrides.temperature = Number($event.target.value); saveOverrides()"
              />
              <button class="ghost" @click="overrides.temperature = ''; saveOverrides()">reset</button>
            </div>
            <small>0 = deterministic, 1 = balanced, 2 = wild. Backend uses 0.1–0.4 by default.</small>
          </label>
          <label class="field">
            <span>Max output tokens</span>
            <input
              v-model.number="overrides.max_tokens"
              type="number" min="64" max="32768" step="64"
              placeholder="default: 4096"
              @change="saveOverrides"
            />
            <small>Higher = longer responses but more cost / latency.</small>
          </label>
          <div class="actions">
            <button class="primary" @click="saveOverrides">Save</button>
            <button class="ghost" @click="resetOverrides">Reset all</button>
          </div>
          <p v-if="overridesActive" class="status ok">
            Overrides active — next chat will use {{ overridesSummary }}.
          </p>
          <p v-else class="status muted">No overrides set. Backend defaults will apply.</p>
        </div>

        <!-- ── RAG Workspace ───────────────────────────────── -->
        <div v-else-if="tab === 'rag'" class="content">
          <p class="hint">
            Drop <code>.md</code>, <code>.txt</code> or <code>.json</code> files. Their text is
            prepended to the LLM user content as <em>USER REFERENCE DOCS</em> on every request.
            Total content is capped at ~12 KB server-side.
          </p>
          <div
            class="dropzone" :class="{ drag: dragOver }"
            @dragover.prevent="dragOver = true"
            @dragleave.prevent="dragOver = false"
            @drop.prevent="onDrop"
            @click="$refs.fileInput.click()"
          >
            <strong>Click or drop files here</strong>
            <small>{{ ragDocs.length }} doc(s) · {{ totalRagBytes }} chars</small>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".md,.txt,.json,text/markdown,text/plain,application/json"
              hidden
              @change="onFilePicked"
            />
          </div>
          <ul v-if="ragDocs.length" class="rag-list">
            <li v-for="(d, i) in ragDocs" :key="`${d.name}-${i}`">
              <div>
                <strong>{{ d.name }}</strong>
                <small>{{ (d.content || '').length }} chars</small>
              </div>
              <button class="ghost danger" @click="removeRag(i)">Remove</button>
            </li>
          </ul>
          <button v-if="ragDocs.length" class="ghost" @click="clearRag">Clear all</button>
          <p v-if="ragError" class="status err">⚠️ {{ ragError }}</p>
        </div>

        <!-- ── Citation Audit ─────────────────────────────── -->
        <div v-else-if="tab === 'cites'" class="content">
          <p class="hint">
            Compares every framework <code>id</code> the model returned in its latest answer
            against the backend KB at <code>/ethics/frameworks</code>. Hallucinated IDs are flagged.
          </p>
          <div v-if="!lastResult" class="empty small">
            No assistant response captured yet. Send a chat with Dev Mode on, then come back.
          </div>
          <div v-else>
            <div class="meta-grid">
              <div><span class="k">Mode</span><span class="badge">{{ lastResult.mode }}</span></div>
              <div><span class="k">References</span><span>{{ citeRefs.length }}</span></div>
              <div><span class="k">In KB</span><span class="ok-text">{{ citeStats.ok }}</span></div>
              <div><span class="k">Hallucinated</span><span :class="citeStats.bad ? 'err-text' : 'muted'">{{ citeStats.bad }}</span></div>
            </div>
            <table v-if="citeRefs.length" class="cite-table">
              <thead><tr><th>ID</th><th>Framework / Article</th><th>Status</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in citeRefs" :key="`${r.id}-${i}`">
                  <td><code>{{ r.id || '(missing id)' }}</code></td>
                  <td>{{ r.framework }} {{ r.article }}<span v-if="r.kbTitle"> · <em>{{ r.kbTitle }}</em></span></td>
                  <td>
                    <span v-if="r.ok" class="finish ok">✓ in KB</span>
                    <span v-else class="finish err">⚠ hallucinated</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty small">This response had no framework references to audit.</p>
          </div>
        </div>

        <!-- ── Eval Harness ───────────────────────────────── -->
        <div v-else-if="tab === 'eval'" class="content">
          <p class="hint">
            Runs {{ evalSet.length }} fixed prompts through <code>/ethics/chat</code> and checks
            whether the auto-classified mode matches the expected one. Uses your current overrides + RAG.
          </p>
          <div class="actions">
            <button class="primary" :disabled="evalRunning" @click="runEval">
              {{ evalRunning ? `Running ${evalProgress}/${evalSet.length}…` : 'Run benchmark' }}
            </button>
            <button v-if="evalResults.length" class="ghost" @click="evalResults = []">Clear</button>
          </div>
          <div v-if="evalResults.length" class="meta-grid">
            <div><span class="k">Cases</span><span>{{ evalResults.length }} / {{ evalSet.length }}</span></div>
            <div><span class="k">Accuracy</span>
              <span :class="evalAccuracy >= 0.8 ? 'ok-text' : 'err-text'">
                {{ Math.round(evalAccuracy * 100) }}%
              </span>
            </div>
            <div><span class="k">Avg latency</span><span>{{ evalAvgMs }} ms</span></div>
            <div><span class="k">Failures</span><span :class="evalFailCount ? 'err-text' : 'muted'">{{ evalFailCount }}</span></div>
          </div>
          <table v-if="evalResults.length" class="cite-table">
            <thead><tr><th>#</th><th>Stake</th><th>Expected</th><th>Got</th><th>ms</th></tr></thead>
            <tbody>
              <tr v-for="(r, i) in evalResults" :key="i">
                <td>{{ i + 1 }}</td>
                <td><code>{{ r.stakeholder }}</code></td>
                <td><code>{{ r.expected }}</code></td>
                <td>
                  <span v-if="r.error" class="finish err" :title="r.error">error</span>
                  <span v-else :class="['finish', r.got === r.expected ? 'ok' : 'err']">{{ r.got }}</span>
                </td>
                <td>{{ r.ms }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        </section>
      </div>

      <footer class="dev-footer">
        <small>Experimental surface — not part of the standard user flow.</small>
      </footer>
    </aside>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { listFrameworks, ethicsChat } from '../api/index.js'

const props = defineProps({
  enabled: { type: Boolean, default: false },
  lastDebug: { type: Object, default: null },
  lastResult: { type: Object, default: null },
})
defineEmits(['close', 'toggle'])

const tab = ref('prompt')
const copied = ref(-1)

// ── Params Switcher state ────────────────────────────────────────
const defaultModel = 'gemini-2.5-flash'
const overrides = reactive({ model: '', temperature: '', max_tokens: '' })
function loadOverrides() {
  try {
    const raw = localStorage.getItem('dev_overrides_v1')
    if (raw) {
      const o = JSON.parse(raw)
      overrides.model = o.model ?? ''
      overrides.temperature = o.temperature ?? ''
      overrides.max_tokens = o.max_tokens ?? ''
    }
  } catch { /* ignore */ }
}
function saveOverrides() {
  const out = {}
  if (overrides.model) out.model = overrides.model
  if (overrides.temperature !== '' && overrides.temperature != null) out.temperature = Number(overrides.temperature)
  if (overrides.max_tokens !== '' && overrides.max_tokens != null) out.max_tokens = Number(overrides.max_tokens)
  if (Object.keys(out).length === 0) localStorage.removeItem('dev_overrides_v1')
  else localStorage.setItem('dev_overrides_v1', JSON.stringify(out))
}
function resetOverrides() {
  overrides.model = ''
  overrides.temperature = ''
  overrides.max_tokens = ''
  localStorage.removeItem('dev_overrides_v1')
}
const overridesActive = computed(
  () => !!overrides.model || overrides.temperature !== '' || overrides.max_tokens !== '',
)
const overridesSummary = computed(() => {
  const parts = []
  if (overrides.model) parts.push(`model=${overrides.model}`)
  if (overrides.temperature !== '') parts.push(`temp=${overrides.temperature}`)
  if (overrides.max_tokens !== '') parts.push(`max=${overrides.max_tokens}`)
  return parts.join(', ')
})

// ── RAG Workspace state ──────────────────────────────────────────
const ragDocs = ref([])
const ragError = ref('')
const dragOver = ref(false)
const RAG_MAX_TOTAL = 50_000 // browser-side soft cap; backend caps at ~12 KB

function loadRag() {
  try {
    const raw = localStorage.getItem('dev_rag_v1')
    if (raw) ragDocs.value = JSON.parse(raw) || []
  } catch { /* ignore */ }
}
function saveRag() {
  if (ragDocs.value.length) localStorage.setItem('dev_rag_v1', JSON.stringify(ragDocs.value))
  else localStorage.removeItem('dev_rag_v1')
}
const totalRagBytes = computed(() => ragDocs.value.reduce((n, d) => n + (d.content?.length || 0), 0))

async function ingestFiles(fileList) {
  ragError.value = ''
  for (const f of fileList) {
    if (!/\.(md|txt|json)$/i.test(f.name)) {
      ragError.value = `Skipped ${f.name}: only .md / .txt / .json supported.`
      continue
    }
    if (f.size > 200_000) {
      ragError.value = `Skipped ${f.name}: file > 200 KB.`
      continue
    }
    const content = await f.text()
    if (totalRagBytes.value + content.length > RAG_MAX_TOTAL) {
      ragError.value = `Skipped ${f.name}: would exceed ${RAG_MAX_TOTAL} char total.`
      continue
    }
    ragDocs.value.push({ name: f.name, content })
  }
  saveRag()
}
function onFilePicked(e) { ingestFiles(Array.from(e.target.files || [])); e.target.value = '' }
function onDrop(e) { dragOver.value = false; ingestFiles(Array.from(e.dataTransfer.files || [])) }
function removeRag(i) { ragDocs.value.splice(i, 1); saveRag() }
function clearRag() { ragDocs.value = []; saveRag() }

// ── Citation Audit state ─────────────────────────────────────────
const kbFrameworks = ref([])
const kbById = computed(() => {
  const m = new Map()
  for (const f of kbFrameworks.value) m.set(f.id, f)
  return m
})

function extractRefs(result) {
  if (!result) return []
  const refs = []
  if (result.mode === 'create' && result.create?.concerns) {
    for (const c of result.create.concerns) {
      for (const r of c.guideline_refs || []) refs.push({ ...r })
    }
  } else if (result.mode === 'validate' && result.validate?.checks) {
    for (const c of result.validate.checks) {
      refs.push({ id: c.id, framework: c.framework, article: c.article, title: c.title })
    }
  }
  // compare mode produces finding ids, not framework ids — skip.
  return refs
}
const citeRefs = computed(() => {
  const refs = extractRefs(props.lastResult)
  return refs.map((r) => {
    const kb = kbById.value.get(r.id)
    return { ...r, ok: !!kb, kbTitle: kb?.title || '' }
  })
})
const citeStats = computed(() => ({
  ok: citeRefs.value.filter((r) => r.ok).length,
  bad: citeRefs.value.filter((r) => !r.ok).length,
}))

// ── Eval Harness state ───────────────────────────────────────────
const evalSet = [
  { stakeholder: 'SEng', expected: 'create',
    prompt: "We're building an AI for radiology image triage. What ethical concerns should I think about regarding patient privacy?" },
  { stakeholder: 'HCP', expected: 'validate',
    prompt: "Validate this requirement: The system shall log every model prediction and the clinician override decision for audit." },
  { stakeholder: 'HCR', expected: 'compare',
    prompt: "Compare this requirement with real-world practice: Patients must be informed when AI is involved in their diagnosis." },
  { stakeholder: 'SEng', expected: 'create',
    prompt: 'Help me draft requirements for handling demographic bias in a sepsis-prediction model.' },
  { stakeholder: 'HCP', expected: 'validate',
    prompt: 'Is this requirement compliant: All patient data shall be encrypted at rest and in transit.' },
]
const evalRunning = ref(false)
const evalProgress = ref(0)
const evalResults = ref([])
const evalAccuracy = computed(() => {
  if (!evalResults.value.length) return 0
  const ok = evalResults.value.filter((r) => !r.error && r.got === r.expected).length
  return ok / evalResults.value.length
})
const evalAvgMs = computed(() => {
  if (!evalResults.value.length) return 0
  return Math.round(evalResults.value.reduce((n, r) => n + (r.ms || 0), 0) / evalResults.value.length)
})
const evalFailCount = computed(
  () => evalResults.value.filter((r) => r.error || r.got !== r.expected).length,
)

async function runEval() {
  evalRunning.value = true
  evalProgress.value = 0
  evalResults.value = []
  // Re-use the same overrides + RAG users have configured.
  let extras = {}
  try {
    const o = JSON.parse(localStorage.getItem('dev_overrides_v1') || '{}')
    if (o.model) extras.model_override = o.model
    if (o.temperature != null && o.temperature !== '') extras.temperature_override = Number(o.temperature)
    if (o.max_tokens != null && o.max_tokens !== '') extras.max_tokens_override = Number(o.max_tokens)
    const docs = JSON.parse(localStorage.getItem('dev_rag_v1') || '[]')
    if (Array.isArray(docs) && docs.length) extras.rag_docs = docs
  } catch { /* ignore */ }

  const tasks = evalSet.map(async (c) => {
    const t0 = performance.now()
    try {
      const res = await ethicsChat({
        prompt: c.prompt, stakeholder: c.stakeholder, ...extras,
      })
      const ms = Math.round(performance.now() - t0)
      evalProgress.value += 1
      return { ...c, got: res.mode, ms, error: null }
    } catch (e) {
      const ms = Math.round(performance.now() - t0)
      evalProgress.value += 1
      return { ...c, got: '—', ms, error: e?.response?.data?.detail || e.message || 'unknown' }
    }
  })
  evalResults.value = await Promise.all(tasks)
  evalRunning.value = false
}

// ── Tab metadata ─────────────────────────────────────────────────
const tabs = [
  { id: 'prompt', short: 'Prompt', label: 'Prompt Inspector',
    desc: 'Inspect the exact system + user prompt sent to Gemini for the latest request.',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>' },
  { id: 'raw',    short: 'Raw',    label: 'Raw Response Viewer',
    desc: 'See the full Gemini JSON response, finish reason and token usage.',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4 4 8l4 4"/><path d="m16 4 4 4-4 4"/><path d="m14 16-4 4"/></svg>' },
  { id: 'rag',    short: 'RAG',    label: 'RAG Workspace',
    desc: 'Upload your own docs (.md / .txt / .json) and let the AI cite them in answers.',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H20v15H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 6.5V19"/></svg>' },
  { id: 'params', short: 'Params', label: 'Model & Params Switcher',
    desc: 'Override model name, temperature and max_tokens per request to A/B test outputs.',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h10"/><circle cx="17" cy="6" r="2"/><path d="M4 18h6"/><circle cx="13" cy="18" r="2"/><path d="M4 12h2"/><circle cx="9" cy="12" r="2"/><path d="M11 12h9"/></svg>' },
  { id: 'cites',  short: 'Cites',  label: 'Citation Audit',
    desc: "Highlight framework IDs the model referenced but the KB doesn't actually contain.",
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1"/><path d="M14 11a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/></svg>' },
  { id: 'eval',   short: 'Eval',   label: 'Eval Harness',
    desc: 'Run a fixed prompt set to compare classification accuracy across runs and models.',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6"/><path d="M10 3v6l-5 9a3 3 0 0 0 2.7 4.5h8.6A3 3 0 0 0 19 18l-5-9V3"/><path d="M7.5 14h9"/></svg>' },
]
const activeTab = computed(() => tabs.find(t => t.id === tab.value) || tabs[0])

const totalUsage = computed(() => {
  const calls = props.lastDebug?.calls || []
  return calls.reduce(
    (acc, c) => ({
      prompt: acc.prompt + (c.usage?.promptTokenCount || 0),
      output: acc.output + (c.usage?.candidatesTokenCount || 0),
    }),
    { prompt: 0, output: 0 },
  )
})

function formatTime(iso) {
  if (!iso) return '–'
  try { return new Date(iso).toLocaleTimeString() } catch { return iso }
}

function finishClass(reason) {
  if (!reason || reason === 'STOP') return 'ok'
  if (reason === 'MAX_TOKENS') return 'warn'
  return 'err'
}

function pretty(obj) {
  try { return JSON.stringify(obj, null, 2) } catch { return String(obj) }
}

async function copy(obj) {
  try {
    await navigator.clipboard.writeText(pretty(obj))
    copied.value = (props.lastDebug?.calls || []).indexOf(
      (props.lastDebug?.calls || []).find((c) => c.raw_response === obj),
    )
    setTimeout(() => { copied.value = -1 }, 1200)
  } catch {
    /* ignore */
  }
}

// Load persisted dev state + KB on mount.
onMounted(async () => {
  loadOverrides()
  loadRag()
  try {
    kbFrameworks.value = await listFrameworks()
  } catch { /* offline ok */ }
})

// Keep `enabled` prop reactive: don't auto-clear data when toggling off,
// so the user can compare before/after, but no need to act on it here.
watch(() => props.enabled, () => {})
</script>

<style scoped>
.dev-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 20, 28, 0.35);
  display: flex; justify-content: flex-end;
  z-index: 1100;
}
.dev-panel {
  width: min(520px, 95vw);
  height: 100%;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.18);
  display: flex; flex-direction: column;
  animation: slideIn 0.18s ease-out;
}
@keyframes slideIn {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}

.dev-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border);
}
.dev-title { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.dev-badge {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  background: #1f2328; color: #fff;
  padding: 2px 6px; border-radius: 4px;
  font-size: 11px;
}
.dev-close {
  background: transparent; border: none;
  font-size: 20px; line-height: 1;
  cursor: pointer; color: var(--color-text-muted);
  width: 28px; height: 28px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  padding: 0;
}
.dev-close:hover { background: var(--color-surface-2); color: var(--color-text); }

.dev-toggle-row {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-2);
}
.toggle-label { font-weight: 600; font-size: 13px; }
.toggle-hint { font-size: 12px; color: var(--color-text-muted); margin-top: 2px; line-height: 1.4; }

.switch { position: relative; width: 38px; height: 22px; flex-shrink: 0; display: inline-block; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; inset: 0; background: #d0d7de; border-radius: 999px; transition: background 0.15s; }
.slider::before {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 18px; height: 18px; background: #fff; border-radius: 50%;
  transition: transform 0.15s; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}
.switch input:checked + .slider { background: #fb8500; }
.switch input:checked + .slider::before { transform: translateX(16px); }

.dev-main {
  flex: 1;
  display: flex;
  min-height: 0;
}
.dev-rail {
  width: 64px;
  flex-shrink: 0;
  background: #1f2328;
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  gap: 2px;
  overflow-y: auto;
}
.dev-rail button {
  background: transparent;
  border: none;
  color: #9ba3af;
  padding: 10px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border-left: 3px solid transparent;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2px;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}
.dev-rail button:hover { color: #fff; background: rgba(255, 255, 255, 0.05); }
.dev-rail button.active {
  color: #fff;
  background: rgba(251, 133, 0, 0.12);
  border-left-color: #fb8500;
}
.rail-icon { display: inline-flex; }
.rail-label { line-height: 1; }

.dev-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  min-width: 0;
}
.section-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--color-text-muted);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}
.soon { display: flex; align-items: center; justify-content: center; min-height: 60%; }
.soon-card {
  text-align: center;
  max-width: 320px;
  padding: 24px;
  border: 1px dashed var(--color-border);
  border-radius: 12px;
  background: var(--color-surface-2);
}
.soon-card h3 { margin: 8px 0 6px; font-size: 15px; }
.soon-card p { margin: 0; font-size: 12.5px; color: var(--color-text-muted); line-height: 1.5; }
.soon-badge {
  display: inline-block;
  background: #fff3cd;
  color: #875200;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 2px 8px;
  border-radius: 999px;
}
.empty {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 32px 8px;
}
.empty .hint { font-size: 12px; margin-top: 6px; }

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 14px;
  font-size: 12px;
  background: var(--color-surface-2);
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 14px;
}
.meta-grid > div { display: flex; justify-content: space-between; gap: 8px; }
.meta-grid .k { color: var(--color-text-muted); }
.badge {
  background: #1f6feb; color: #fff; padding: 1px 6px;
  border-radius: 4px; font-size: 11px; font-weight: 600;
}

.user-prompt { margin-bottom: 14px; }
.user-prompt h4 { margin: 0 0 6px; font-size: 12px; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.4px; }

.call {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 12px;
  background: var(--color-surface);
}
.call-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-2);
  font-size: 12px;
  border-radius: 8px 8px 0 0;
}
.call-num { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700; }
.model { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--color-text-muted); }
.cfg { margin-left: auto; color: var(--color-text-muted); font-size: 11px; }
.finish { margin-left: auto; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.finish.ok { background: #ddf4e3; color: #1f6f3b; }
.finish.warn { background: #fff3cd; color: #875200; }
.finish.err { background: #ffd6d3; color: #a40e26; }

.usage-row {
  padding: 6px 12px;
  font-size: 11px;
  color: var(--color-text-muted);
  display: flex; gap: 12px;
  border-bottom: 1px solid var(--color-border);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.call details { padding: 8px 12px; border-bottom: 1px solid var(--color-border); }
.call details:last-of-type { border-bottom: none; }
.call summary { cursor: pointer; font-size: 12px; font-weight: 600; color: var(--color-text-muted); }
.call summary:hover { color: var(--color-text); }
.call pre, .user-prompt pre {
  margin: 8px 0 0;
  background: #0d1117;
  color: #e6edf3;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 11.5px;
  line-height: 1.45;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.copy-btn {
  margin: 8px 12px 12px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
}
.copy-btn:hover { background: #eef0f3; }

.feature-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.feature-list li {
  background: var(--color-surface-2);
  border: 1px dashed var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  display: flex; flex-direction: column; gap: 2px;
}
.feature-list li strong { font-weight: 700; }
.feature-list li span { color: var(--color-text-muted); font-size: 12px; line-height: 1.4; }

.dev-footer {
  padding: 10px 18px;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

/* ── Generic helpers used by Params / RAG / Cites / Eval ───────── */
.hint { font-size: 12.5px; color: var(--color-text-muted); margin: 0 0 12px; line-height: 1.5; }
.hint code { background: var(--color-surface-2); padding: 1px 4px; border-radius: 3px; font-size: 11px; }
.empty.small { padding: 18px 8px; font-size: 12.5px; }

.field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px; font-size: 12.5px; }
.field > span { font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
.field > span em { color: var(--color-text-muted); font-style: normal; font-weight: 400; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.field input[type="text"], .field input[type="number"] {
  border: 1px solid var(--color-border); border-radius: 6px;
  padding: 6px 8px; font-size: 13px; background: #fff;
}
.field input[type="range"] { flex: 1; }
.field small { color: var(--color-text-muted); font-size: 11px; }
.field .row { display: flex; gap: 8px; align-items: center; }

.actions { display: flex; gap: 8px; margin: 8px 0 12px; }
.primary {
  background: #fb8500; color: #fff; border: none;
  padding: 6px 14px; border-radius: 6px; font-size: 12.5px; font-weight: 600;
  cursor: pointer;
}
.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.ghost {
  background: transparent; border: 1px solid var(--color-border);
  padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer;
  color: var(--color-text);
}
.ghost:hover { background: var(--color-surface-2); }
.ghost.danger { color: #a40e26; border-color: #ffd6d3; }
.ghost.danger:hover { background: #ffd6d3; }

.status { font-size: 12px; padding: 8px 10px; border-radius: 6px; margin-top: 4px; }
.status.ok { background: #ddf4e3; color: #1f6f3b; }
.status.err { background: #ffd6d3; color: #a40e26; }
.status.muted { background: var(--color-surface-2); color: var(--color-text-muted); }
.ok-text { color: #1f6f3b; font-weight: 600; }
.err-text { color: #a40e26; font-weight: 600; }
.muted { color: var(--color-text-muted); }

.dropzone {
  border: 2px dashed var(--color-border);
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  background: var(--color-surface-2);
  transition: border-color 0.15s, background 0.15s;
  display: flex; flex-direction: column; gap: 4px;
  margin-bottom: 12px;
}
.dropzone strong { font-size: 13px; }
.dropzone small { font-size: 11px; color: var(--color-text-muted); }
.dropzone.drag, .dropzone:hover { border-color: #fb8500; background: #fff7ec; }

.rag-list { list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rag-list li {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 8px 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 12px;
}
.rag-list li strong { display: block; font-size: 12.5px; word-break: break-all; }
.rag-list li small { color: var(--color-text-muted); font-size: 11px; }

.cite-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
  margin-top: 8px;
}
.cite-table th, .cite-table td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: top;
}
.cite-table th {
  background: var(--color-surface-2);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--color-text-muted);
}
.cite-table code { font-size: 11px; word-break: break-all; }
</style>
