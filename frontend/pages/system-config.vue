<script setup lang="ts">
/**
 * System Configuration Page
 *
 * Phase 1: Device Placement
 * - Drag-and-drop device placement
 * - Titan-native (grid-aligned) and third-party (free) devices
 * - Device properties editing
 * - Layer visibility controls
 * - Zoom/pan canvas
 */

import type { DeckConfig, MoverState } from '~/types/deck'
import type { Device, DeviceTemplate, LayerVisibility } from '~/types/device'
import { useDeviceManager } from '~/composables/useDeviceManager'

// Device manager composable
const deviceManager = useDeviceManager()

// API base URL
const config = useRuntimeConfig()
const apiBase = config.public.apiBase || ''

// Deck and mover state
const deck = ref<DeckConfig | null>(null)
const movers = ref<MoverState[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Load deck configuration
async function loadDeck() {
  try {
    const response = await fetch(`${apiBase}/api/deck`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    deck.value = await response.json()
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

// Load initial data
async function loadData() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([loadDeck(), loadMovers()])
    // Load saved devices from backend
    await deviceManager.loadDevices()
  } catch (e) {
    error.value = `Failed to load data: ${e}`
  } finally {
    loading.value = false
  }
}

// Handle device drop from palette
function handleDropDevice(template: DeviceTemplate, position: { x: number; y: number }) {
  deviceManager.addDevice(template, position)
}

// Handle device selection
function handleSelectDevice(deviceId: string | null) {
  deviceManager.selectDevice(deviceId)
}

// Handle device move
function handleMoveDevice(deviceId: string, position: { x: number; y: number }) {
  deviceManager.moveDevice(deviceId, position)
}

// Handle device move end (with undo)
function handleMoveDeviceEnd(deviceId: string, position: { x: number; y: number }) {
  deviceManager.moveDeviceWithUndo(deviceId, position)
}

// Handle device rotation (with specific angle)
function handleRotateDevice(deviceId: string, angle: number) {
  deviceManager.setDeviceOrientation(deviceId, angle)
}

// Handle device update from properties panel
function handleUpdateDevice(updates: Partial<Device>) {
  if (deviceManager.selectedDeviceId.value) {
    deviceManager.updateDevice(deviceManager.selectedDeviceId.value, updates)
  }
}

// Handle device delete
function handleDeleteDevice() {
  if (deviceManager.selectedDeviceId.value) {
    deviceManager.deleteDevice(deviceManager.selectedDeviceId.value)
  }
}

// Handle layer toggle
function handleToggleLayer(layer: keyof LayerVisibility) {
  deviceManager.toggleLayer(layer)
}

// Save configuration
async function saveConfig() {
  await deviceManager.saveDevices()
}

// Zoom controls
function handleZoomIn() {
  deviceManager.zoomIn()
}

function handleZoomOut() {
  deviceManager.zoomOut()
}

function handleZoomFit() {
  if (!deck.value) return

  // Get deck bounds
  const bounds = {
    minX: 0,
    minY: 0,
    maxX: deck.value.width_mm,
    maxY: deck.value.height_mm
  }

  // TODO: Get canvas viewport size
  deviceManager.zoomToFit(bounds, { width: 1200, height: 800 })
}

function handleResetView() {
  deviceManager.resetView()
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  // Ignore if in input field
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
    return
  }

  // Undo/Redo
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
    e.preventDefault()
    if (e.shiftKey) {
      deviceManager.redo()
    } else {
      deviceManager.undo()
    }
    return
  }

  if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
    e.preventDefault()
    deviceManager.redo()
    return
  }

  // Delete
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (deviceManager.selectedDeviceId.value) {
      handleDeleteDevice()
    }
    return
  }

  // Rotate
  if (e.key === 'r' || e.key === 'R') {
    if (deviceManager.selectedDeviceId.value) {
      deviceManager.rotateDevice(deviceManager.selectedDeviceId.value, !e.shiftKey)
    }
    return
  }

  // Escape to deselect
  if (e.key === 'Escape') {
    deviceManager.selectDevice(null)
    return
  }

  // Save
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    saveConfig()
    return
  }
}

// Handle beforeunload to save changes when closing tab
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (deviceManager.isDirty.value) {
    // Trigger sync save before unload
    deviceManager.saveBeforeNavigation()
    // Show confirmation dialog
    e.preventDefault()
    e.returnValue = ''
  }
}

// Lifecycle
onMounted(async () => {
  await loadData()
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(async () => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  // Save any pending changes before navigation
  await deviceManager.saveBeforeNavigation()
  deviceManager.cleanup()
})
</script>

<template>
  <div class="system-config-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-section">
        <h1 class="toolbar-title">System Configuration</h1>
      </div>

      <div class="toolbar-section toolbar-actions">
        <button
          class="btn btn-icon"
          :disabled="!deviceManager.canUndo.value"
          title="Undo (Ctrl+Z)"
          @click="deviceManager.undo()"
        >
          ↶
        </button>
        <button
          class="btn btn-icon"
          :disabled="!deviceManager.canRedo.value"
          title="Redo (Ctrl+Y)"
          @click="deviceManager.redo()"
        >
          ↷
        </button>

        <span class="toolbar-divider" />

        <button class="btn btn-icon" title="Zoom In" @click="handleZoomIn">+</button>
        <span class="zoom-display">{{ (deviceManager.zoom.value * 100).toFixed(0) }}%</span>
        <button class="btn btn-icon" title="Zoom Out" @click="handleZoomOut">−</button>
        <button class="btn btn-secondary" title="Fit to View" @click="handleZoomFit">Fit</button>
        <button class="btn btn-secondary" title="Reset View" @click="handleResetView">Reset</button>

        <span class="toolbar-divider" />

        <span v-if="deviceManager.isDirty.value" class="save-indicator unsaved" title="Changes will auto-save">
          ●
        </span>
        <span v-else class="save-indicator saved" title="All changes saved">
          ✓
        </span>

        <button
          class="btn btn-primary"
          :disabled="deviceManager.loading.value || !deviceManager.isDirty.value"
          @click="saveConfig"
        >
          {{ deviceManager.loading.value ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error || deviceManager.error.value" class="error-banner">
      {{ error || deviceManager.error.value }}
      <button @click="error = null; deviceManager.error.value = null">Dismiss</button>
    </div>

    <!-- Main content -->
    <div class="content-grid">
      <!-- Left sidebar: Device palette -->
      <div class="sidebar sidebar-left">
        <ConfigDevicePalette
          @open-device-hub-dialog="() => { /* TODO: Open dialog */ }"
        />
      </div>

      <!-- Main canvas -->
      <div class="main-canvas">
        <div v-if="loading" class="loading">
          Loading configuration...
        </div>
        <ConfigWorkcellCanvas
          v-else
          :deck="deck"
          :devices="deviceManager.devices.value"
          :movers="movers"
          :selected-device-id="deviceManager.selectedDeviceId.value"
          :zoom="deviceManager.zoom.value"
          :pan-x="deviceManager.panX.value"
          :pan-y="deviceManager.panY.value"
          :layers="deviceManager.layers.value"
          :is-dragging="deviceManager.isDragging.value"
          @update:zoom="(z) => deviceManager.setZoom(z)"
          @update:pan-x="(x) => deviceManager.panX.value = x"
          @update:pan-y="(y) => deviceManager.panY.value = y"
          @select-device="handleSelectDevice"
          @move-device="handleMoveDevice"
          @move-device-end="handleMoveDeviceEnd"
          @rotate-device="handleRotateDevice"
          @drop-device="handleDropDevice"
        />
      </div>

      <!-- Right sidebar: Properties and Layers -->
      <div class="sidebar sidebar-right">
        <div class="sidebar-section">
          <h3 class="section-header">Properties</h3>
          <ConfigDeviceProperties
            :device="deviceManager.selectedDevice.value"
            @update="handleUpdateDevice"
            @delete="handleDeleteDevice"
            @rotate="(cw) => deviceManager.selectedDeviceId.value && deviceManager.rotateDevice(deviceManager.selectedDeviceId.value, cw)"
          />
        </div>

        <div class="sidebar-section">
          <ConfigLayerControls
            :layers="deviceManager.layers.value"
            @toggle="handleToggleLayer"
          />
        </div>

        <!-- Status -->
        <div class="sidebar-section status-section">
          <div class="status-grid">
            <div class="status-item">
              <span class="status-value">{{ deviceManager.devices.value.length }}</span>
              <span class="status-label">Devices</span>
            </div>
            <div class="status-item">
              <span class="status-value">{{ deck?.tiles.length || 0 }}</span>
              <span class="status-label">Tiles</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.system-config-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #2c3e50;
  color: white;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  /* Full-bleed: counteract layout padding */
  margin: calc(-1 * var(--space-4));
  width: calc(100% + 2 * var(--space-4));
  height: calc(100% + 2 * var(--space-4));
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 15px;
  background: #34495e;
  border-bottom: 1px solid #2c3e50;
  flex-shrink: 0;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #3498db;
  margin: 0;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-actions {
  gap: 8px;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: #4a6278;
  margin: 0 4px;
}

.zoom-display {
  font-size: 12px;
  color: #bdc3c7;
  min-width: 45px;
  text-align: center;
}

.save-indicator {
  font-size: 14px;
  transition: color 0.3s ease;
}

.save-indicator.unsaved {
  color: #f1c40f;
  animation: pulse 1.5s ease-in-out infinite;
}

.save-indicator.saved {
  color: #2ecc71;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  width: 28px;
  height: 28px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: #2c3e50;
  color: #bdc3c7;
}

.btn-icon:hover:not(:disabled) {
  background: #3d566e;
  color: white;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-secondary {
  background: #34495e;
  color: #bdc3c7;
}

.btn-secondary:hover:not(:disabled) {
  background: #3d566e;
  color: white;
}

.error-banner {
  background: #e74c3c;
  color: white;
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.error-banner button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 4px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
}

.content-grid {
  display: flex;
  flex: 1;
  min-height: 0;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #2c3e50;
  padding: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.sidebar-left {
  border-right: 1px solid #34495e;
}

.sidebar-right {
  border-left: 1px solid #34495e;
}

.sidebar-section {
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid #34495e;
}

.sidebar-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.section-header {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #3498db;
  margin: 0 0 8px 0;
}

.main-canvas {
  flex: 1;
  min-width: 0;
  background: white;
  position: relative;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #7f8c8d;
  background: white;
}

.status-section {
  margin-top: auto;
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
  font-size: 18px;
  font-weight: 700;
  color: #3498db;
}

.status-label {
  font-size: 10px;
  color: #bdc3c7;
}
</style>
