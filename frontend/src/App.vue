<template>
  <router-view />
</template>

<script setup>
// All chrome (sidebar / header) lives inside the chat view.
// Login & OAuth callback views render full-viewport themselves.
</script>

<style scoped>
/* No global chrome — keep the route in charge of its own layout. */
</style>
