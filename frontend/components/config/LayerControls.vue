<script setup lang="ts">
/**
 * LayerControls - Toggle-able layer visibility
 *
 * Layers:
 * - Tiles (stator grid)
 * - Devices (all device graphics)
 * - Tracks (track lines)
 * - Teach Points (waypoints, queues, pivots)
 * - Movers (mover positions)
 * - Labels (device names, IDs)
 */

import type { LayerVisibility } from '~/types/device'

const props = defineProps<{
  layers: LayerVisibility
}>()

const emit = defineEmits<{
  (e: 'toggle', layer: keyof LayerVisibility): void
}>()

// Layer definitions
const layerDefs: { key: keyof LayerVisibility; label: string; shortcut: string }[] = [
  { key: 'tiles', label: 'Tiles', shortcut: '1' },
  { key: 'devices', label: 'Devices', shortcut: '2' },
  { key: 'tracks', label: 'Tracks', shortcut: '3' },
  { key: 'teachPoints', label: 'Teach Points', shortcut: '4' },
  { key: 'movers', label: 'Movers', shortcut: '5' },
  { key: 'labels', label: 'Labels', shortcut: '6' }
]

// Handle keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  // Only handle if not in input field
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
    return
  }

  const layer = layerDefs.find(l => l.shortcut === e.key)
  if (layer) {
    emit('toggle', layer.key)
  }
}

// Lifecycle
onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="layer-controls">
    <h3 class="section-header">Layers</h3>

    <div class="layer-list">
      <label
        v-for="layer in layerDefs"
        :key="layer.key"
        class="layer-item"
      >
        <input
          type="checkbox"
          :checked="layers[layer.key]"
          @change="emit('toggle', layer.key)"
        >
        <span class="layer-label">{{ layer.label }}</span>
        <span class="layer-shortcut">{{ layer.shortcut }}</span>
      </label>
    </div>

    <div class="layer-help">
      <p>Press number keys to toggle layers</p>
    </div>
  </div>
</template>

<style scoped>
.layer-controls {
  display: flex;
  flex-direction: column;
}

.section-header {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #3498db;
  margin: 0 0 12px 0;
}

.layer-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #34495e;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.layer-item:hover {
  background: #3d566e;
}

.layer-item input[type="checkbox"] {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: #3498db;
}

.layer-label {
  flex: 1;
  font-size: 12px;
  color: white;
}

.layer-shortcut {
  font-size: 10px;
  color: #95a5a6;
  background: #2c3e50;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.layer-help {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #34495e;
}

.layer-help p {
  font-size: 10px;
  color: #95a5a6;
  margin: 0;
}
</style>
