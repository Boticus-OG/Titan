<script setup lang="ts">
// Default layout with header and main content area
</script>

<template>
  <div class="layout">
    <header class="header">
      <div class="header-brand">
        <h1 class="header-title">TITAN</h1>
        <span class="header-subtitle">XPlanar Workflow Orchestrator</span>
      </div>
      <nav class="header-nav">
        <NuxtLink to="/" class="nav-link">Deck</NuxtLink>
        <NuxtLink to="/workflows" class="nav-link">Workflows</NuxtLink>
        <NuxtLink to="/actors" class="nav-link">Actors</NuxtLink>
      </nav>
      <div class="header-status">
        <span class="status-indicator status-connected"></span>
        <span class="status-text">Connected</span>
      </div>
    </header>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.header-brand {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.header-title {
  font-size: var(--text-xl);
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--color-primary);
}

.header-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.header-nav {
  display: flex;
  gap: var(--space-4);
}

.nav-link {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.nav-link:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-elevated);
}

.nav-link.router-link-active {
  color: var(--color-primary);
  background: rgba(99, 102, 241, 0.1);
}

.header-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-connected {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
}

.status-disconnected {
  background: var(--color-error);
}

.status-text {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.main {
  flex: 1;
  padding: var(--space-4);
}
</style>
