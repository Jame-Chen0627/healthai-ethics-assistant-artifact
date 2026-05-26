<template>
  <div class="modal-backdrop" @click.self="$emit('cancel')">
    <div class="modal">
      <h2>Start a new chat</h2>
      <p class="lead">Start a HealthAI Ethics chat and choose the role you'll be advising as. The assistant tailors its tone, citations and examples accordingly.</p>

      <!-- Topic selection -->
      <label class="ctx-label">Topic</label>
      <div class="topic-grid">
        <button
          v-for="t in TOPICS"
          :key="t.id"
          class="topic-card"
          :class="{ selected: selectedTopic === t.id }"
          @click="selectTopic(t.id)"
        >
          <div class="topic-icon">{{ t.icon }}</div>
          <div class="topic-name">{{ t.name }}</div>
          <div class="topic-desc">{{ t.desc }}</div>
        </button>
      </div>

      <div v-if="selectedTopic === 'custom'" class="custom-panel">
        <label class="ctx-label">Custom topic name</label>
        <input
          v-model="customTopicName"
          type="text"
          maxlength="80"
          placeholder="e.g. Smart-Home IoT Privacy Requirements"
          class="text-input"
        />
        <label class="ctx-label">Topic description / system prompt</label>
        <p class="hint">Describe the domain and what kind of requirements / guidelines / real-world findings the assistant should reason about. Create / Validate / Compare modules will use this as background.</p>
        <textarea
          v-model="customTopicPrompt"
          rows="4"
          placeholder="e.g. We are designing a consumer smart-home hub. Focus on privacy, vendor lock-in, and child safety. Reference GDPR, CCPA, and IoT security guidelines."
        />
      </div>

      <!-- Chat name (the user's note for this chat) -->
      <label class="ctx-label">Chat name (note)</label>
      <input
        v-model="chatName"
        type="text"
        maxlength="80"
        placeholder="Optional \u2014 e.g. Sprint-3 privacy review"
        class="text-input"
      />

      <!-- Persona selection -->
      <label class="ctx-label">User persona</label>
      <div class="role-grid">
        <button
          v-for="r in ROLES"
          :key="r.id"
          class="role-card"
          :class="{ selected: selected === r.id }"
          @click="selectRole(r.id)"
        >
          <div class="role-icon">{{ r.icon }}</div>
          <div class="role-name">{{ r.name }}</div>
          <div class="role-desc">{{ r.desc }}</div>
        </button>
      </div>

      <div v-if="selected === 'custom'" class="custom-panel">
        <label class="ctx-label">Let System Decide</label>
        <p class="hint">
          Answer the short questionnaire so the assistant can infer a mixed persona.
          You can be a software engineer, healthcare professional, healthcare researcher,
          or a combination of all three.
        </p>
        <div class="survey-head">
          <span>{{ answeredCount }} / {{ PERSONA_QUESTIONS.length }} answered</span>
          <span v-if="!personaSurveyComplete">Complete all questions to continue</span>
        </div>
        <div class="survey-list">
          <div v-for="(q, idx) in PERSONA_QUESTIONS" :key="q.id" class="survey-item">
            <div class="survey-question">
              <span class="q-num">{{ idx + 1 }}</span>
              <span>{{ q.text }}</span>
            </div>
            <div class="survey-options" role="group" :aria-label="q.text">
              <button
                v-for="opt in PERSONA_OPTIONS"
                :key="opt.value"
                type="button"
                class="survey-option"
                :class="{ selected: personaAnswers[q.id] === opt.value }"
                @click="setPersonaAnswer(q.id, opt.value)"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>
        </div>
        <div class="persona-preview">
          <div class="pp-name">{{ personaSummary.name }}</div>
          <pre class="pp-body">{{ personaSummary.body }}</pre>
        </div>
      </div>

      <label class="ctx-label">Project context (optional)</label>
      <textarea
        v-model="systemContext"
        rows="2"
        placeholder="e.g., A diagnostic imaging AI that triages chest X-rays in emergency departments."
      />

      <div class="actions">
        <button class="secondary" @click="$emit('cancel')">Cancel</button>
        <button class="primary" :disabled="!canConfirm" @click="confirm">
          Start chat
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const TOPICS = [
  { id: 'healthai-ethics',       icon: '⚕️', name: 'HealthAI Ethics',           desc: 'Healthcare AI ethical requirements (default KB)' },
]

// Future adaptive-domain topics are intentionally hidden from the current
// HealthAI-focused UI: cybersecurity, mobile UX, education curriculum, and
// custom topic prompting can be restored when the adaptive scope is active.

const ROLES = [
  { id: 'HCP',    icon: '🩺', name: 'Healthcare Professional', desc: 'Clinician, nurse, radiologist' },
  { id: 'SEng',   icon: '💻', name: 'Software Engineer',       desc: 'Building AI / software systems' },
  { id: 'HCR',    icon: '🔬', name: 'Healthcare Researcher',   desc: 'AI-related health research' },
  { id: 'custom', icon: '🧭', name: 'Let System Decide',       desc: '20-question mixed persona' },
]

const ROLE_LABELS = {
  HCP: 'Healthcare Professional',
  SEng: 'Software Engineer',
  HCR: 'Healthcare Researcher',
}

const PERSONA_OPTIONS = [
  { label: 'No', value: 0 },
  { label: 'Some', value: 1 },
  { label: 'Yes', value: 2 },
]

const PERSONA_QUESTIONS = [
  { id: 'q01', text: 'I design, build, or maintain software systems.', weights: { SEng: 3 } },
  { id: 'q02', text: 'I can read or write code, APIs, databases, or deployment scripts.', weights: { SEng: 3 } },
  { id: 'q03', text: 'I think about system architecture, scalability, reliability, or security controls.', weights: { SEng: 3 } },
  { id: 'q04', text: 'I translate stakeholder needs into technical specifications or user stories.', weights: { SEng: 2, HCR: 1 } },
  { id: 'q05', text: 'I am involved in implementing privacy, access control, audit logging, or compliance features.', weights: { SEng: 2, HCP: 1, HCR: 1 } },
  { id: 'q06', text: 'I understand clinical workflows, hospital routines, or patient care pathways.', weights: { HCP: 3 } },
  { id: 'q07', text: 'I interpret or work with medical records, scans, lab results, or patient observations.', weights: { HCP: 3 } },
  { id: 'q08', text: 'I am responsible for patient safety, clinical judgement, or care quality.', weights: { HCP: 3 } },
  { id: 'q09', text: 'I need AI outputs to fit into real clinical decision-making.', weights: { HCP: 2, HCR: 1 } },
  { id: 'q10', text: 'I communicate risks, recommendations, or system limitations to clinicians or patients.', weights: { HCP: 2, HCR: 1 } },
  { id: 'q11', text: 'I design or evaluate research studies, protocols, or experiments.', weights: { HCR: 3 } },
  { id: 'q12', text: 'I collect, clean, analyse, or interpret healthcare datasets for research.', weights: { HCR: 3 } },
  { id: 'q13', text: 'I work with ethics approval, informed consent, participant recruitment, or research governance.', weights: { HCR: 3, HCP: 1 } },
  { id: 'q14', text: 'I evaluate model performance, validity, generalisability, or evidence quality.', weights: { HCR: 2, SEng: 1 } },
  { id: 'q15', text: 'I care about fairness, bias, representativeness, or subgroup performance in AI systems.', weights: { HCR: 2, SEng: 1, HCP: 1 } },
  { id: 'q16', text: 'I use standards, regulations, or ethical frameworks to justify requirements.', weights: { HCR: 2, SEng: 1, HCP: 1 } },
  { id: 'q17', text: 'I interview users, analyse stakeholder needs, or gather requirements.', weights: { HCR: 1, SEng: 2, HCP: 1 } },
  { id: 'q18', text: 'I help introduce, train, or support users when a new healthcare technology is deployed.', weights: { HCP: 2, SEng: 1 } },
  { id: 'q19', text: 'I often bridge communication between clinical, research, and technical teams.', weights: { HCP: 1, SEng: 1, HCR: 1 } },
  { id: 'q20', text: 'I want the assistant to balance implementation detail, clinical usefulness, and research evidence.', weights: { HCP: 1, SEng: 1, HCR: 1 } },
]

const selectedTopic = ref('healthai-ethics')
const customTopicName = ref('')
const customTopicPrompt = ref('')
const chatName = ref('')

const selected = ref('SEng')
const systemContext = ref('')
const personaAnswers = ref({})

const emit = defineEmits(['confirm', 'cancel'])

function selectTopic(id) {
  selectedTopic.value = id
}

function selectRole(id) {
  selected.value = id
}

const activeTopic = computed(() => TOPICS.find((t) => t.id === selectedTopic.value) || TOPICS[0])

const resolvedTopicLabel = computed(() => {
  if (selectedTopic.value === 'custom') return (customTopicName.value || '').trim() || 'Custom Topic'
  return activeTopic.value.name
})

const canConfirm = computed(() => {
  if (!selected.value) return false
  if (selectedTopic.value === 'custom') {
    if (!customTopicName.value.trim()) return false
    if (!customTopicPrompt.value.trim()) return false
  }
  if (selected.value === 'custom') return personaSurveyComplete.value
  return true
})

const answeredCount = computed(() => Object.keys(personaAnswers.value).length)
const personaSurveyComplete = computed(() => answeredCount.value === PERSONA_QUESTIONS.length)

function setPersonaAnswer(id, value) {
  personaAnswers.value = { ...personaAnswers.value, [id]: value }
}

const personaProfile = computed(() => {
  const scores = { HCP: 0, SEng: 0, HCR: 0 }
  const maxScores = { HCP: 0, SEng: 0, HCR: 0 }
  const positiveAnswers = []

  for (const q of PERSONA_QUESTIONS) {
    for (const [role, weight] of Object.entries(q.weights)) {
      maxScores[role] += 2 * weight
    }
    const value = personaAnswers.value[q.id]
    if (value == null) continue
    for (const [role, weight] of Object.entries(q.weights)) {
      scores[role] += value * weight
    }
    if (value > 0) positiveAnswers.push({ question: q.text, answer: value === 2 ? 'Yes' : 'Some' })
  }

  const percentages = Object.fromEntries(
    Object.entries(scores).map(([role, score]) => [
      role,
      maxScores[role] ? Math.round((score / maxScores[role]) * 100) : 0,
    ])
  )
  const ranked = Object.keys(scores).sort((a, b) => scores[b] - scores[a])
  const topScore = scores[ranked[0]] || 0
  const selectedRoles = ranked.filter((role) => scores[role] > 0 && scores[role] >= topScore * 0.55)
  const roles = selectedRoles.length ? selectedRoles : ['SEng']

  return { scores, percentages, roles, positiveAnswers }
})

const personaSummary = computed(() => {
  const roleNames = personaProfile.value.roles.map((r) => ROLE_LABELS[r])
  const scoreText = Object.entries(personaProfile.value.percentages)
    .map(([role, pct]) => `${ROLE_LABELS[role]} ${pct}%`)
    .join(' · ')
  return {
    name: `Inferred persona: ${roleNames.join(' + ')}`,
    body: `${scoreText}\nThe assistant will balance these perspectives when creating, validating, or comparing requirements.`,
  }
})

const personaText = computed(() => {
  if (!personaSurveyComplete.value) return ''
  const roleNames = personaProfile.value.roles.map((r) => ROLE_LABELS[r])
  return JSON.stringify(
    {
      persona_source: 'Let System Decide questionnaire',
      inferred_persona: roleNames.join(' + '),
      role_mix_percentages: personaProfile.value.percentages,
      selected_role_codes: personaProfile.value.roles,
      interpretation:
        'The user may combine multiple perspectives. Tailor responses to this mixed persona rather than assuming a single fixed role.',
      response_guidance: [
        personaProfile.value.roles.includes('SEng') ? 'Include implementable software, architecture, data, security, and logging details.' : null,
        personaProfile.value.roles.includes('HCP') ? 'Explain implications for clinical workflow, patient safety, and healthcare professionals.' : null,
        personaProfile.value.roles.includes('HCR') ? 'Include research validity, evidence quality, ethics approval, bias, and evaluation considerations.' : null,
      ].filter(Boolean),
      questionnaire_answers: personaProfile.value.positiveAnswers,
    },
    null,
    2
  )
})

const customPersonaName = computed(() => {
  if (selected.value !== 'custom') return null
  const roleNames = personaProfile.value.roles.map((r) => ROLE_LABELS[r])
  if (!personaSurveyComplete.value) return 'Let System Decide'
  if (roleNames.length === 1) return roleNames[0]
  return `Mixed: ${roleNames.join(' + ')}`
})

const resolvedStakeholder = computed(() => {
  if (selected.value !== 'custom') return selected.value
  const roles = personaProfile.value.roles
  if (roles.includes('SEng')) return 'SEng'
  if (roles.includes('HCP')) return 'HCP'
  if (roles.includes('HCR')) return 'HCR'
  return 'SEng'
})

function confirm() {
  const isCustomPersona = selected.value === 'custom'
  const isCustomTopic = selectedTopic.value === 'custom'
  const BUILTIN_PROMPTS = {
    'healthai-ethics': '', // backend default
  }
  const topicLabel = resolvedTopicLabel.value
  const topicPrompt = isCustomTopic
    ? customTopicPrompt.value.trim()
    : (BUILTIN_PROMPTS[selectedTopic.value] || '')

  emit('confirm', {
    topic: topicLabel,
    topicPrompt: topicPrompt || null,
    chatName: chatName.value.trim() || null,
    // Backend still requires one primary stakeholder code; the mixed persona
    // itself is passed through customPersona.
    stakeholder: isCustomPersona ? resolvedStakeholder.value : selected.value,
    systemContext: systemContext.value.trim() || null,
    customPersona: isCustomPersona ? personaText.value : null,
    customPersonaName: isCustomPersona ? customPersonaName.value : null,
  })
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 20, 28, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: var(--color-surface);
  border-radius: 12px;
  padding: 24px;
  width: min(620px, 92vw);
  max-height: 90vh; overflow-y: auto;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
}
h2 { margin: 0 0 4px; font-size: 18px; }
.lead { color: var(--color-text-muted); margin: 0 0 16px; font-size: 13px; }

.topic-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.topic-card {
  background: var(--color-surface-2);
  border: 2px solid var(--color-border);
  border-radius: 10px;
  padding: 10px 6px;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s;
}
.topic-card:hover { border-color: var(--color-accent); }
.topic-card.selected { border-color: var(--color-accent); background: #ddf4ff; }
.topic-icon { font-size: 22px; margin-bottom: 2px; }
.topic-name { font-size: 12px; font-weight: 700; }
.topic-desc { font-size: 10.5px; color: var(--color-text-muted); margin-top: 2px; line-height: 1.3; }

.role-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.role-card {
  background: var(--color-surface-2);
  border: 2px solid var(--color-border);
  border-radius: 10px;
  padding: 14px 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s;
}
.role-card:hover { border-color: var(--color-accent); }
.role-card.selected { border-color: var(--color-accent); background: #ddf4ff; }
.role-icon { font-size: 26px; margin-bottom: 4px; }
.role-name { font-size: 13px; font-weight: 700; }
.role-desc { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }

.custom-panel {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.custom-panel .hint {
  margin: 4px 0 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.survey-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--color-text-muted);
  font-size: 11.5px;
  font-weight: 600;
  margin-bottom: 8px;
}
.survey-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 360px;
  overflow: auto;
  padding-right: 4px;
}
.survey-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 8px;
}
.survey-question {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12.5px;
  line-height: 1.4;
}
.q-num {
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 700;
}
.survey-options {
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(48px, 1fr));
  gap: 4px;
}
.survey-option {
  border: 1px solid var(--color-border);
  background: var(--color-surface-2);
  color: var(--color-text-muted);
  border-radius: 6px;
  min-height: 28px;
  padding: 4px 7px;
  font-size: 11.5px;
  font-weight: 650;
  cursor: pointer;
}
.survey-option:hover {
  border-color: var(--color-accent);
  color: var(--color-text);
}
.survey-option.selected {
  background: #ddf4ff;
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.persona-preview {
  margin-top: 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 8px;
}
.pp-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.pp-body {
  margin: 0;
  max-height: 140px;
  overflow: auto;
  font-size: 11px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-text-muted);
}

.ctx-label { display: block; font-size: 12px; color: var(--color-text-muted); font-weight: 600; margin: 8px 0 4px; }
textarea, .text-input {
  width: 100%; box-sizing: border-box;
  border: 1px solid var(--color-border);
  border-radius: 6px; padding: 8px; font-size: 13px; font-family: inherit;
}
textarea { resize: vertical; }
.text-input { margin-bottom: 4px; }

.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
@media (max-width: 720px) {
  .topic-grid { grid-template-columns: 1fr; }
  .role-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 420px) {
  .topic-grid { grid-template-columns: 1fr; }
  .role-grid { grid-template-columns: 1fr; }
  .survey-item { grid-template-columns: 1fr; }
}
</style>
