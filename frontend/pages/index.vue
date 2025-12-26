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
  height: 100%;
  display: flex;
  background: #2c3e50;
  color: white;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  /* Full-bleed: counteract layout padding */
  margin: calc(-1 * var(--space-4));
  width: calc(100% + 2 * var(--space-4));
  height: calc(100% + 2 * var(--space-4));
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
  display: flex;
  width: 100%;
  height: 100%;
  gap: 0;
}

/* Main deck area - matches Track Designer canvas area */
.deck-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: #f0f0f0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 15px;
  background: #34495e;
  color: white;
}

.panel-header h2 {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #3498db;
  margin: 0;
}

.panel-actions {
  display: flex;
  gap: 6px;
}

.panel-actions .btn {
  width: auto;
  margin-bottom: 0;
  padding: 6px 12px;
  font-size: 12px;
}

/* Side panel - matches Track Designer sidebar */
.side-panel {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  background: #2c3e50;
  padding: 15px;
  overflow-y: auto;
  min-height: 0;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #7f8c8d;
  background: #ecf0f1;
}

/* Cards - Track Designer section style */
.card {
  background: transparent;
  border: none;
  padding: 0;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #34495e;
}

.card:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.card-header {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #3498db;
  margin-bottom: 12px;
}

/* Inspector */
.inspector {
  flex-shrink: 0;
}

.inspector-content h3 {
  font-size: var(--text-sm);
  font-weight: 600;
  margin-bottom: 10px;
  color: white;
}

.inspector-empty {
  text-align: center;
  padding: 15px;
  color: #7f8c8d;
}

.info-list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 12px;
  font-size: 12px;
}

.info-list dt {
  color: #95a5a6;
}

.info-list dd {
  color: white;
}

/* Status Card */
.status-card {
  flex-shrink: 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background: #34495e;
  padding: 10px 8px;
  border-radius: 4px;
}

.status-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: #3498db;
}

.status-label {
  font-size: var(--text-xs);
  color: #bdc3c7;
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
  padding: 0;
}

.debug-info {
  background: #34495e;
  padding: 6px 12px;
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: #bdc3c7;
}

/* Badge overrides for dark theme */
.badge {
  font-weight: 600;
}

.badge-success {
  background: rgba(39, 174, 96, 0.3);
  color: #2ecc71;
}

.badge-warning {
  background: rgba(243, 156, 18, 0.3);
  color: #f39c12;
}

.badge-info {
  background: rgba(52, 152, 219, 0.3);
  color: #3498db;
}
</style>
