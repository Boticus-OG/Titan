<script setup lang="ts">
/**
 * Deck Editor Page
 *
 * Full-featured deck configuration interface with:
 * - Visual tile editor
 * - Track drawing tool
 * - Location teaching
 * - Station boundary configuration
 * - Real-time mover monitoring
 */

import type { DeckConfig, Track, Location, MoverState } from '~/types/deck'

// API base URL
const apiBase = 'http://localhost:8000'

// State
const deck = ref<DeckConfig | null>(null)
const movers = ref<MoverState[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const saving = ref(false)

// Load deck configuration
async function loadDeck() {
  try {
    const response = await fetch(`${apiBase}/api/deck`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    deck.value = await response.json()

    // Ensure tracks and locations arrays exist
    if (!deck.value!.tracks) deck.value!.tracks = []
    if (!deck.value!.locations) deck.value!.locations = []
  } catch (e) {
    console.error('Failed to load deck:', e)
    error.value = `Failed to load deck: ${e}`
  }
}

// Load movers
async function loadMovers() {
  try {
    const response = await fetch(`${apiBase}/api/movers`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    movers.value = Object.values(data)
  } catch (e) {
    console.error('Failed to load movers:', e)
  }
}

// Toggle tile
async function handleTileToggle(col: number, row: number, enabled: boolean) {
  try {
    saving.value = true
    const response = await fetch(`${apiBase}/api/deck/editor/tiles/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ col, row, enabled }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await loadDeck()
  } catch (e) {
    console.error('Failed to toggle tile:', e)
    error.value = `Failed to toggle tile: ${e}`
  } finally {
    saving.value = false
  }
}

// Create track
async function handleTrackCreated(track: Partial<Track>) {
  try {
    saving.value = true
    const response = await fetch(`${apiBase}/api/deck/tracks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(track),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await loadDeck()
  } catch (e) {
    console.error('Failed to create track:', e)
    error.value = `Failed to create track: ${e}`
  } finally {
    saving.value = false
  }
}

// Delete track
async function handleTrackDeleted(trackId: number) {
  try {
    saving.value = true
    const response = await fetch(`${apiBase}/api/deck/tracks/${trackId}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await loadDeck()
  } catch (e) {
    console.error('Failed to delete track:', e)
    error.value = `Failed to delete track: ${e}`
  } finally {
    saving.value = false
  }
}

// Create location
async function handleLocationCreated(location: Partial<Location>) {
  try {
    saving.value = true
    const response = await fetch(`${apiBase}/api/deck/locations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(location),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await loadDeck()
  } catch (e) {
    console.error('Failed to create location:', e)
    error.value = `Failed to create location: ${e}`
  } finally {
    saving.value = false
  }
}

// Update location position
async function handleLocationUpdated(locationId: string, x: number, y: number) {
  try {
    saving.value = true
    const response = await fetch(`${apiBase}/api/deck/locations/${locationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await loadDeck()
  } catch (e) {
    console.error('Failed to update location:', e)
    error.value = `Failed to update location: ${e}`
  } finally {
    saving.value = false
  }
}

// Delete location
async function handleLocationDeleted(locationId: string) {
  try {
    saving.value = true
    const response = await fetch(`${apiBase}/api/deck/locations/${locationId}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    await loadDeck()
  } catch (e) {
    console.error('Failed to delete location:', e)
    error.value = `Failed to delete location: ${e}`
  } finally {
    saving.value = false
  }
}

// Export configuration
async function exportConfig() {
  try {
    const response = await fetch(`${apiBase}/api/deck/editor/export`, {
      method: 'POST',
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()

    // Download as JSON file
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `deck-config-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to export config:', e)
    error.value = `Failed to export: ${e}`
  }
}

// Refresh data
async function refresh() {
  await Promise.all([loadDeck(), loadMovers()])
}

// Periodic mover update
let updateInterval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  loading.value = true
  await refresh()
  loading.value = false

  // Update movers every 500ms
  updateInterval = setInterval(() => {
    loadMovers()
  }, 500)
})

onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
})
</script>

<template>
  <div class="deck-editor-page">
    <!-- Error banner -->
    <div v-if="error" class="error-banner">
      {{ error }}
      <button @click="error = null">Dismiss</button>
    </div>

    <!-- Page header -->
    <div class="page-header">
      <div class="header-left">
        <NuxtLink to="/" class="back-link">&larr; Back to Deck View</NuxtLink>
        <h1>Deck Editor</h1>
      </div>
      <div class="header-actions">
        <span v-if="saving" class="saving-indicator">Saving...</span>
        <button class="btn btn-secondary" @click="refresh">Refresh</button>
        <button class="btn btn-primary" @click="exportConfig">Export</button>
      </div>
    </div>

    <!-- Main content -->
    <div class="editor-content">
      <div v-if="loading" class="loading">
        Loading deck configuration...
      </div>

      <DeckEditor
        v-else-if="deck"
        :deck="deck"
        :movers="movers"
        @tile-toggle="handleTileToggle"
        @track-created="handleTrackCreated"
        @track-deleted="handleTrackDeleted"
        @location-created="handleLocationCreated"
        @location-updated="handleLocationUpdated"
        @location-deleted="handleLocationDeleted"
      />

      <div v-else class="loading">
        No deck configuration available. Is the backend running?
      </div>
    </div>
  </div>
</template>

<style scoped>
.deck-editor-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.error-banner {
  background: var(--color-error);
  color: white;
  padding: var(--space-3);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-banner button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.back-link {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-decoration: none;
}

.back-link:hover {
  color: var(--color-primary);
}

.page-header h1 {
  font-size: var(--text-xl);
  font-weight: 600;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.saving-indicator {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.editor-content {
  flex: 1;
  overflow: hidden;
  display: flex;
}

.loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.btn {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  filter: brightness(1.1);
}

.btn-secondary {
  background: var(--color-surface-elevated);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover {
  background: var(--color-surface-hover);
}
</style>
