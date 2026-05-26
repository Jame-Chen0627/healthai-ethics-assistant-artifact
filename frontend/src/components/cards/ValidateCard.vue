<template>
  <div class="card-stack">
    <div class="card-banner validate">
      <span class="badge">Validate Requirements</span>
      <span v-if="data?.summary" class="hint">{{ data.summary }}</span>
    </div>
    <div v-if="!data?.checks?.length" class="empty">No checks returned.</div>
    <div v-for="(c, idx) in data.checks" :key="idx" class="concern-card validate">
      <div class="concern-head row">
        <GuidelineRefBadge :item="c" />
        <span class="status-pill" :class="statusClass(c.status)">{{ statusLabel(c.status) }}</span>
      </div>
      <p v-if="c.gap" class="concern-desc">{{ c.gap }}</p>
      <div v-if="c.suggested_addition" class="req-block">
        <div class="block-label">Suggested addition</div>
        <div class="req-text">→ {{ c.suggested_addition }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import GuidelineRefBadge from '../GuidelineRefBadge.vue'

defineProps({ data: { type: Object, required: true } })

function statusLabel(s) {
  return { valid: '✓ Valid', missing: '⚠ Missing', not_applicable: '— N/A' }[s] || s
}
function statusClass(s) {
  return { valid: 'pill-green', missing: 'pill-red', not_applicable: 'pill-grey' }[s] || 'pill-grey'
}
</script>

<style scoped>
@import './card-shared.css';
.card-banner.validate { background: var(--color-validate-soft); color: var(--color-validate); }
.concern-card.validate { border-left: 4px solid var(--color-validate); }
.row { flex-wrap: wrap; gap: 8px; }
.status-pill {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 600; border: 1px solid transparent;
}
.pill-green { background: #dafbe1; color: var(--color-success); border-color: #4ac26b66; }
.pill-red   { background: #ffebe9; color: var(--color-error); border-color: #ff818266; }
.pill-grey  { background: var(--color-surface-2); color: var(--color-text-muted); border-color: var(--color-border); }
</style>
