<template>
  <div class="coverage" aria-label="Ethical dimension coverage">
    <button
      v-for="dim in DIMENSIONS"
      :key="dim.id"
      type="button"
      class="coverage-btn"
      :class="[{ covered: counts[dim.id] > 0 }, dim.className]"
      :aria-pressed="counts[dim.id] > 0"
      :title="`${dim.label}: ${counts[dim.id] > 0 ? `${counts[dim.id]} related item(s)` : 'not covered in this response'}`"
    >
      <span class="dot" aria-hidden="true"></span>
      <span class="label">{{ dim.label }}</span>
      <span class="count">{{ counts[dim.id] || 0 }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
})

const DIMENSIONS = [
  { id: 'privacy', label: 'Privacy', className: 'privacy' },
  { id: 'safety', label: 'Safety', className: 'safety' },
  { id: 'bias', label: 'Bias', className: 'bias' },
  { id: 'transparency', label: 'Transparency', className: 'transparency' },
  { id: 'accountability', label: 'Accountability', className: 'accountability' },
]

const FRAMEWORK_DIMENSIONS = {
  'eu-ai-act-art-9': ['safety', 'accountability'],
  'eu-ai-act-art-10': ['privacy', 'bias'],
  'eu-ai-act-art-12': ['accountability', 'transparency', 'privacy'],
  'eu-ai-act-art-13': ['transparency'],
  'eu-ai-act-art-14': ['safety', 'accountability'],
  'eu-ai-act-art-15': ['safety', 'bias'],
  'nist-govern-1-5': ['accountability', 'privacy'],
  'nist-map-1-5': ['privacy', 'transparency'],
  'nist-measure-2-3': ['safety', 'bias'],
  'nist-measure-2-11': ['bias'],
}

const KEYWORD_DIMENSIONS = [
  { id: 'privacy', patterns: [/privacy/i, /patient data/i, /personal data/i, /consent/i, /encrypt/i, /access/i, /retention/i] },
  { id: 'safety', patterns: [/safety/i, /harm/i, /risk/i, /robust/i, /accuracy/i, /failure/i, /oversight/i] },
  { id: 'bias', patterns: [/bias/i, /fairness/i, /representative/i, /demographic/i, /subgroup/i] },
  { id: 'transparency', patterns: [/transparen/i, /explain/i, /instruction/i, /limitation/i, /communicat/i, /trace/i] },
  { id: 'accountability', patterns: [/accountab/i, /audit/i, /log/i, /record/i, /monitor/i, /review/i, /responsib/i] },
]

const counts = computed(() => {
  const out = Object.fromEntries(DIMENSIONS.map((d) => [d.id, 0]))
  const add = (dimension) => {
    if (dimension && out[dimension] !== undefined) out[dimension] += 1
  }
  const addMany = (dimensions) => {
    for (const d of dimensions || []) add(d)
  }

  const msg = props.message || {}
  if (msg.mode === 'create') {
    for (const concern of msg.create?.concerns || []) add(concern.dimension)
  } else if (msg.mode === 'compare') {
    for (const suggestion of msg.compare?.suggestions || []) add(suggestion.dimension)
  } else if (msg.mode === 'validate') {
    for (const check of msg.validate?.checks || []) {
      const fromFramework = FRAMEWORK_DIMENSIONS[check.id] || []
      if (fromFramework.length) {
        addMany(fromFramework)
        continue
      }
      const text = [
        check.framework,
        check.article,
        check.title,
        check.gap,
        check.suggested_addition,
      ].filter(Boolean).join(' ')
      for (const item of KEYWORD_DIMENSIONS) {
        if (item.patterns.some((p) => p.test(text))) add(item.id)
      }
    }
  }

  return out
})
</script>

<style scoped>
.coverage {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-width: 100%;
}

.coverage-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: var(--color-surface-2);
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 650;
  cursor: default;
  white-space: nowrap;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.55;
}

.count {
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid var(--color-border);
  font-size: 10px;
}

.coverage-btn.covered.privacy { background: #ddf4ff; color: var(--color-accent); border-color: #54aeff66; }
.coverage-btn.covered.safety { background: #ffebe9; color: var(--color-error); border-color: #ff818266; }
.coverage-btn.covered.bias { background: #fff8c5; color: var(--color-warning); border-color: #d4a72c66; }
.coverage-btn.covered.transparency { background: #dafbe1; color: var(--color-success); border-color: #4ac26b66; }
.coverage-btn.covered.accountability { background: #f6f8fa; color: var(--color-text); border-color: var(--color-border); }

@media (max-width: 640px) {
  .coverage-btn {
    flex: 1 1 calc(50% - 6px);
    justify-content: space-between;
  }
}
</style>
