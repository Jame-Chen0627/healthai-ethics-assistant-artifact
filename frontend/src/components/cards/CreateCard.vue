<template>
  <div class="card-stack">
    <div class="card-banner create">
      <span class="badge">Create Requirements</span>
      <span class="hint">Drafted from your concern, grounded in EU AI Act / NIST AI RMF.</span>
    </div>
    <div v-if="!data?.concerns?.length" class="empty">No concerns generated.</div>
    <div v-for="(c, idx) in data.concerns" :key="idx" class="concern-card">
      <div class="concern-head">
        <span class="dim-badge" :class="dimClass(c.dimension)">{{ c.dimension }}</span>
        <strong>{{ c.title }}</strong>
      </div>
      <p class="concern-desc">{{ c.description }}</p>
      <div class="req-block">
        <div class="block-label">Requirement</div>
        <div class="req-text">{{ c.requirement }}</div>
      </div>
      <div class="req-actions">
        <button
          type="button"
          class="req-action accept"
          :class="{ active: prefStatus(c) === 'accepted' }"
          @click="emitPreference('accepted', c, idx)"
        >
          {{ prefStatus(c) === 'accepted' ? 'Accepted' : 'Accept' }}
        </button>
        <button
          type="button"
          class="req-action reject"
          :class="{ active: prefStatus(c) === 'rejected' }"
          @click="emitPreference('rejected', c, idx)"
        >
          {{ prefStatus(c) === 'rejected' ? 'Rejected' : 'Reject' }}
        </button>
        <button
          type="button"
          class="req-action suppress"
          :class="{ active: prefStatus(c) === 'suppressed' }"
          @click="emitPreference('suppressed', c, idx)"
        >
          {{ prefStatus(c) === 'suppressed' ? 'Cleared from this chat' : 'Clear from this chat' }}
        </button>
      </div>
      <div v-if="c.guideline_refs?.length" class="refs">
        <div class="block-label">Guideline references</div>
        <GuidelineRefBadge v-for="r in c.guideline_refs" :key="r.id" :item="r" />
      </div>
    </div>
  </div>
</template>

<script setup>
import GuidelineRefBadge from '../GuidelineRefBadge.vue'

const props = defineProps({
  data: { type: Object, required: true },
  preferences: { type: Array, default: () => [] },
  sourceMessageId: { type: Number, default: null },
})
const emit = defineEmits(['requirement-action'])

function reqKey(text) {
  return (text || '').trim().toLowerCase().replace(/\s+/g, ' ')
}

function prefStatus(c) {
  const key = reqKey(c.requirement)
  return props.preferences.find((p) => (
    p.requirement_key === key || reqKey(p.requirement_text) === key
  ))?.status || null
}

function emitPreference(status, c) {
  emit('requirement-action', {
    status,
    title: c.title || '',
    dimension: c.dimension || '',
    description: c.description || '',
    requirement_text: c.requirement || '',
    guideline_refs: c.guideline_refs || [],
    source_message_id: props.sourceMessageId,
  })
}

function dimClass(d) {
  return {
    privacy: 'badge-blue', safety: 'badge-red', bias: 'badge-yellow',
    transparency: 'badge-green', accountability: 'badge-grey',
  }[d] || 'badge-grey'
}
</script>

<style scoped>
@import './card-shared.css';
.card-banner.create { background: var(--color-create-soft); color: var(--color-create); }
.concern-card { border-left: 4px solid var(--color-create); }
.req-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: -2px 0 8px;
}
.req-action {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  border-radius: 999px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
}
.req-action:hover { border-color: var(--color-accent); color: var(--color-accent); }
.req-action.accept.active { background: #dafbe1; border-color: #4ac26b66; color: var(--color-success); }
.req-action.reject.active { background: #ffebe9; border-color: #ff818266; color: var(--color-error); }
.req-action.suppress.active { background: #fff8c5; border-color: #d4a72c66; color: var(--color-warning); }
</style>
