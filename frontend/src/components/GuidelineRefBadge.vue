<template>
  <button
    type="button"
    class="ref-badge"
    :style="{ background: bg, color: fg, borderColor: border }"
    :aria-label="`Open regulation detail for ${item.framework} ${item.article}`"
    @click="openDetail"
  >
    <strong>{{ item.framework }}</strong>
    <span class="dot">·</span>
    <span>{{ item.article }}</span>
    <span v-if="item.title" class="ref-title">({{ item.title }})</span>
  </button>

  <Teleport to="body">
    <div v-if="detailOpen" class="reg-backdrop" @click.self="closeDetail">
      <section class="reg-dialog" role="dialog" aria-modal="true" :aria-label="dialogTitle">
        <header class="reg-header">
          <div>
            <div class="reg-kicker">{{ detail.framework || item.framework }}</div>
            <h3>{{ detail.article || item.article }} · {{ detail.title || item.title || 'Regulation detail' }}</h3>
          </div>
          <button type="button" class="reg-close" aria-label="Close regulation detail" @click="closeDetail">×</button>
        </header>

        <div class="reg-body">
          <p v-if="detail.summary" class="reg-summary">{{ detail.summary }}</p>
          <p v-else class="reg-summary muted">
            No stored regulation detail is available for this custom reference yet.
          </p>
          <p v-if="detail.detail" class="reg-detail">{{ detail.detail }}</p>

          <div v-if="detail.applies_to?.length" class="reg-meta">
            <span class="meta-label">Applies to</span>
            <span v-for="dim in detail.applies_to" :key="dim" class="dim-chip">{{ dim }}</span>
          </div>

          <div class="reg-id">
            <span class="meta-label">Reference ID</span>
            <code>{{ detail.id || item.id || 'custom-reference' }}</code>
          </div>

          <a
            v-if="detail.source_url"
            class="source-link"
            :href="detail.source_url"
            target="_blank"
            rel="noreferrer"
          >
            Open {{ detail.source_label || 'source document' }}
          </a>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { listFrameworks } from '../api'

const props = defineProps({ item: { type: Object, required: true } })

let frameworkCache = null
const detailOpen = ref(false)
const kbDetail = ref(null)
const loading = ref(false)

const FRAMEWORK_COLORS = {
  'EU AI Act':   { bg: '#f3e8ff', fg: '#6f42c1', border: '#a371f766' },
  'NIST AI RMF': { bg: '#ddf4ff', fg: '#0969da', border: '#54aeff66' },
}

const palette = computed(() => FRAMEWORK_COLORS[props.item.framework] || { bg: '#f0f2f5', fg: '#656d76', border: '#d1d9e0' })
const bg = computed(() => palette.value.bg)
const fg = computed(() => palette.value.fg)
const border = computed(() => palette.value.border)
const detail = computed(() => ({ ...props.item, ...(kbDetail.value || {}) }))
const dialogTitle = computed(() => `${detail.value.framework || props.item.framework} ${detail.value.article || props.item.article}`)

async function openDetail() {
  detailOpen.value = true
  if (kbDetail.value || loading.value || !props.item.id) return
  loading.value = true
  try {
    if (!frameworkCache) frameworkCache = await listFrameworks()
    kbDetail.value = frameworkCache.find((f) => f.id === props.item.id) || null
  } catch {
    kbDetail.value = null
  } finally {
    loading.value = false
  }
}

function closeDetail() {
  detailOpen.value = false
}
</script>

<style scoped>
.ref-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 999px;
  font-size: 12px; border: 1px solid;
  margin: 2px 4px 2px 0;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s;
}
.ref-badge:hover {
  box-shadow: 0 2px 8px rgba(31, 35, 40, 0.12);
  transform: translateY(-1px);
}
.ref-badge:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.dot { opacity: 0.5; }
.ref-title { opacity: 0.75; font-style: italic; }

.reg-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1300;
  background: rgba(15, 20, 28, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.reg-dialog {
  width: min(560px, 94vw);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  box-shadow: 0 18px 45px rgba(31, 35, 40, 0.22);
  overflow: hidden;
}
.reg-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--color-border);
}
.reg-kicker {
  color: v-bind(fg);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.reg-header h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
  color: var(--color-text);
}
.reg-close {
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 24px;
  line-height: 1;
  width: 30px;
  height: 30px;
  border-radius: 6px;
}
.reg-close:hover { background: var(--color-surface-2); color: var(--color-text); }
.reg-body {
  padding: 16px 18px 18px;
}
.reg-summary {
  margin: 0 0 14px;
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.55;
}
.reg-detail {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.55;
  margin: 0 0 14px;
  padding: 10px 12px;
}
.muted { color: var(--color-text-muted); }
.reg-meta,
.reg-id {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.meta-label {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.dim-chip {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  color: var(--color-text);
  font-size: 12px;
  padding: 2px 8px;
}
.reg-id code {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  color: var(--color-text);
  font-size: 12px;
  padding: 2px 6px;
}
.source-link {
  display: inline-flex;
  margin-top: 14px;
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}
.source-link:hover { text-decoration: underline; }
</style>
