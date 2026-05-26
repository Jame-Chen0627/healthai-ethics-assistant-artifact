<template>
  <div class="msg" :class="role">
    <div class="bubble" v-if="role === 'user'">{{ message.content }}</div>
    <div class="assistant-block" v-else>
      <DimensionCoverage v-if="showCoverage" :message="message" />
      <div v-if="message.assistant_text" class="bubble assistant">
        {{ message.assistant_text }}
      </div>
      <CreateCard
        v-if="message.mode === 'create' && message.create"
        :data="message.create"
        :preferences="requirementPreferences"
        :source-message-id="message.message_id"
        @requirement-action="$emit('requirement-action', $event)"
      />
      <ValidateCard v-else-if="message.mode === 'validate' && message.validate" :data="message.validate" />
      <CompareCard v-else-if="message.mode === 'compare' && message.compare" :data="message.compare" />
      <div v-else-if="message.error" class="bubble error">⚠️ {{ message.error }}</div>
      <div v-else-if="message.pending" class="bubble assistant">
        <span class="thinking-dot"></span><span class="thinking-dot"></span><span class="thinking-dot"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CreateCard from './cards/CreateCard.vue'
import ValidateCard from './cards/ValidateCard.vue'
import CompareCard from './cards/CompareCard.vue'
import DimensionCoverage from './DimensionCoverage.vue'

const props = defineProps({
  role: { type: String, required: true }, // 'user' | 'assistant'
  message: { type: Object, required: true },
  requirementPreferences: { type: Array, default: () => [] },
})

defineEmits(['requirement-action'])

const showCoverage = computed(() => {
  if (props.role !== 'assistant') return false
  if (props.message?.pending || props.message?.error) return false
  return ['create', 'validate', 'compare'].includes(props.message?.mode)
})
</script>

<style scoped>
.msg {
  display: flex;
  width: 100%;
  margin-bottom: 18px;
}
.msg.user { justify-content: flex-end; }
.msg.assistant { justify-content: flex-start; }

.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg.user .bubble {
  background: var(--color-accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.bubble.assistant {
  background: var(--color-surface-2);
  color: var(--color-text);
  border-bottom-left-radius: 4px;
}
.bubble.error {
  background: #ffebe9;
  color: var(--color-error);
  border: 1px solid #ff818266;
}

.assistant-block {
  max-width: 88%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.thinking-dot {
  display: inline-block;
  width: 6px; height: 6px; margin: 0 2px;
  background: var(--color-text-muted);
  border-radius: 50%;
  animation: blink 1.2s infinite ease-in-out;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}
</style>
