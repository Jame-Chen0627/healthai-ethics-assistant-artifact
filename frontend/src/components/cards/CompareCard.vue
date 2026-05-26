<template>
  <div class="card-stack">
    <div class="card-banner compare">
      <span class="badge">Compare with Real-World Scenarios</span>
      <span class="hint">Practitioner & online-discussion findings.</span>
    </div>
    <div class="concern-card req-original">
      <div class="block-label">Original requirement</div>
      <div class="req-text">{{ data.original_requirement }}</div>
    </div>
    <div
      v-for="(s, idx) in data.suggestions"
      :key="idx"
      class="sug-card"
      :class="s.source === 'interview' ? 'src-interview' : 'src-reddit'"
    >
      <div class="concern-head row">
        <span class="src-badge" :class="s.source === 'interview' ? 'src-interview' : 'src-reddit'">
          {{ s.source === 'interview' ? '🎙 Interview' : '💬 Reddit' }}
        </span>
        <span class="dim-badge badge-grey">{{ s.dimension }}</span>
        <span class="dim-badge badge-grey">{{ s.stakeholder }}</span>
      </div>
      <blockquote class="quote">"{{ s.quote }}"</blockquote>
      <div class="rec">→ Consider: {{ s.recommendation }}</div>
    </div>
    <div class="concern-card req-enhanced">
      <div class="block-label">Enhanced requirement</div>
      <div class="req-text">{{ data.enhanced_requirement }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({ data: { type: Object, required: true } })
</script>

<style scoped>
@import './card-shared.css';
.card-banner.compare { background: var(--color-compare-soft); color: var(--color-compare); }
.req-original { border-left: 4px solid var(--color-validate); }
.req-enhanced { border-left: 4px solid var(--color-compare); background: #fffbe6; }
.sug-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
}
.sug-card.src-interview { border-left: 4px solid var(--color-interview); background: #fafffa; }
.sug-card.src-reddit    { border-left: 4px solid var(--color-reddit);    background: #fffdf6; }
.row { flex-wrap: wrap; gap: 6px; }
.src-badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 600;
}
.src-badge.src-interview { background: #dafbe1; color: var(--color-interview); }
.src-badge.src-reddit    { background: #fff8c5; color: var(--color-reddit); }
.quote {
  border-left: 3px solid var(--color-border);
  margin: 8px 0; padding: 4px 10px; color: var(--color-text);
  font-style: italic; font-size: 13px;
}
.rec { font-size: 13px; color: var(--color-text); }
</style>
