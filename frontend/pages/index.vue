<script setup lang="ts">
/**
 * Main Deck View Page
 *
 * Constitution Section 5.1: Plate-Centric Primary View
 * Constitution Section 5.2: Drill-Down Capability
 */

import type { DeckConfig, MoverState, PlateState, Station } from '~/types/deck'

// State
const deck = ref<DeckConfig | null>(null)
const movers = ref<MoverState[]>([])
const plates = ref<PlateState[]>([])
const selectedStation = ref<Station | null>(null)
const selectedMover = ref<MoverState | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const demoRunning = ref(false)

// API base URL
const apiBase = 'http://localhost:8000'

// Load deck configuration
async function loadDeck() {
  try {
    const response = await fetch(`${apiBase}/api/deck`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    deck.value = await response.json()
  }
  catch (e) {
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
  }
  catch (e) {
    console.error('Failed to load movers:', e)
  }
}

// Load plates
async function loadPlates() {
  try {
    const response = await fetch(`${apiBase}/api/plates`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    plates.value = Object.values(data)
  }
  catch (e) {
    console.error('Failed to load plates:', e)
  }
}

// Run demo
async function runDemo() {
  if (demoRunning.value) return

  demoRunning.value = true
  console.log('Starting demo...')

  try {
    const response = await fetch(`${apiBase}/api/demo/run`, { method: 'POST' })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    const result = await response.json()
    console.log('Demo started:', result)

    // Poll for updates while demo runs
    const pollInterval = setInterval(async () => {
      await loadPlates()
      await loadMovers()

      // Check if any plate is still running
      const activePlates = plates.value.filter(p =>
        p.phase !== 'completed' && p.phase !== 'error' && p.phase !== 'aborted'
      )
      if (activePlates.length === 0 && plates.value.length > 0) {
        clearInterval(pollInterval)
        demoRunning.value = false
        console.log('Demo completed!')
      }
    }, 500)

    // Safety timeout - stop polling after 60 seconds
    setTimeout(() => {
      clearInterval(pollInterval)
      demoRunning.value = false
    }, 60000)
  }
  catch (e) {
    console.error('Failed to run demo:', e)
    error.value = `Failed to run demo: ${e}`
    demoRunning.value = false
  }
}

// Refresh all data
async function refresh() {
  await Promise.all([loadDeck(), loadMovers(), loadPlates()])
}

// Handle station selection
function onSelectStation(station: Station) {
  selectedStation.value = station
  selectedMover.value = null
}

// Handle mover selection
function onSelectMover(mover: MoverState) {
  selectedMover.value = mover
  selectedStation.value = null
}

// Load data on mount (client-side only)
onMounted(async () => {
  loading.value = true
  await refresh()
  loading.value = false
})
</script>

<template>
  <div class="deck-page">
    <!-- Error message -->
    <div v-if="error" class="error-banner">
      {{ error }}
      <button @click="error = null">Dismiss</button>
    </div>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- Deck Visualization -->
      <div class="deck-panel">
        <div class="panel-header">
          <h2>Deck View</h2>
          <div class="panel-actions">
            <button
              class="btn btn-primary"
              :disabled="demoRunning"
              @click="runDemo"
            >
              {{ demoRunning ? 'Running...' : 'Run Demo' }}
            </button>
            <button class="btn btn-secondary" @click="refresh">
              Refresh
            </button>
          </div>
        </div>

        <div v-if="loading" class="loading">
          Loading deck configuration...
        </div>
        <div v-else-if="deck" class="deck-wrapper">
          <!-- Debug info -->
          <div class="debug-info">
            Deck: {{ deck.cols }}x{{ deck.rows }} |
            Stations: {{ deck.stations?.length || 0 }} |
            Movers: {{ movers.length }}
          </div>
          <DeckView
            :deck="deck"
            :movers="movers"
            :plates="plates"
            @select-station="onSelectStation"
            @select-mover="onSelectMover"
          />
        </div>
        <div v-else class="loading">
          No deck configuration available. Is the backend running?
        </div>
      </div>

      <!-- Side Panel -->
      <div class="side-panel">
        <!-- Inspector -->
        <div class="card inspector">
          <div class="card-header">
            Inspector
          </div>

          <!-- Station Details -->
          <div v-if="selectedStation" class="inspector-content">
            <h3>{{ selectedStation.name }}</h3>
            <dl class="info-list">
              <dt>Station ID</dt>
              <dd>{{ selectedStation.station_id }}</dd>
              <dt>Device Type</dt>
              <dd>{{ selectedStation.device_type }}</dd>
              <dt>Device ID</dt>
              <dd>{{ selectedStation.device_id }}</dd>
              <dt>Grid Position</dt>
              <dd>({{ selectedStation.grid_pos.col }}, {{ selectedStation.grid_pos.row }})</dd>
              <dt>Position (mm)</dt>
              <dd>{{ selectedStation.position.x }}, {{ selectedStation.position.y }}</dd>
              <dt>Status</dt>
              <dd>
                <span :class="selectedStation.is_available ? 'badge badge-success' : 'badge badge-warning'">
                  {{ selectedStation.is_available ? 'Available' : 'Occupied' }}
                </span>
              </dd>
              <dt>Slots</dt>
              <dd>{{ selectedStation.occupied_slots }} / {{ selectedStation.slots }}</dd>
            </dl>
          </div>

          <!-- Mover Details -->
          <div v-else-if="selectedMover" class="inspector-content">
            <h3>Mover {{ selectedMover.mover_id }}</h3>
            <dl class="info-list">
              <dt>State</dt>
              <dd>
                <span
                  :class="{
                    'badge badge-success': selectedMover.physical?.state === 'idle',
                    'badge badge-info': selectedMover.physical?.state === 'transporting',
                    'badge badge-warning': selectedMover.physical?.state === 'assigned',
                  }"
                >
                  {{ selectedMover.physical?.state || 'unknown' }}
                </span>
              </dd>
              <dt>Position (mm)</dt>
              <dd class="mono">
                X: {{ selectedMover.physical?.position?.x?.toFixed(1) || 0 }}<br>
                Y: {{ selectedMover.physical?.position?.y?.toFixed(1) || 0 }}<br>
                C: {{ selectedMover.physical?.position?.c?.toFixed(1) || 0 }}
              </dd>
              <dt>Available</dt>
              <dd>{{ selectedMover.available ? 'Yes' : 'No' }}</dd>
              <dt>Assigned Plate</dt>
              <dd>{{ selectedMover.assigned_plate_id || 'None' }}</dd>
            </dl>
          </div>

          <!-- Default -->
          <div v-else class="inspector-empty">
            <p class="text-muted">
              Click on a station or mover to inspect
            </p>
          </div>
        </div>

        <!-- System Status -->
        <div class="card status-card">
          <div class="card-header">
            System Status
          </div>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-value">{{ movers.length }}</span>
              <span class="status-label">Movers</span>
            </div>
            <div class="status-item">
              <span class="status-value">{{ plates.length }}</span>
              <span class="status-label">Plates</span>
            </div>
            <div class="status-item">
              <span class="status-value">{{ deck?.stations.length || 0 }}</span>
              <span class="status-label">Stations</span>
            </div>
            <div class="status-item">
              <span class="status-value">{{ deck?.cols || 0 }}x{{ deck?.rows || 0 }}</span>
              <span class="status-label">Grid</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.deck-page {
  height: calc(100vh - 60px);
  overflow: hidden;
}

.error-banner {
  background: var(--color-error);
  color: white;
  padding: var(--space-3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  border-radius: var(--radius-sm);
}

.error-banner button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-4);
  height: 100%;
}

.deck-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.panel-header h2 {
  font-size: var(--text-lg);
  font-weight: 600;
}

.panel-actions {
  display: flex;
  gap: var(--space-2);
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow-y: auto;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--color-text-muted);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
}

/* Inspector */
.inspector {
  flex-shrink: 0;
}

.inspector-content h3 {
  font-size: var(--text-base);
  font-weight: 600;
  margin-bottom: var(--space-3);
}

.inspector-empty {
  text-align: center;
  padding: var(--space-4);
}

.info-list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
}

.info-list dt {
  color: var(--color-text-muted);
}

.info-list dd {
  color: var(--color-text-primary);
}

/* Status Card */
.status-card {
  flex-shrink: 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.status-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-primary);
}

.status-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.deck-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.debug-info {
  background: var(--color-surface-elevated);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}
</style>
