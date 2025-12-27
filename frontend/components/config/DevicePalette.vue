<script setup lang="ts">
/**
 * DevicePalette - Drag-and-drop device palette
 *
 * Shows available device templates organized by class:
 * - Titan Native (grid-aligned)
 * - Third Party (free placement)
 * - DeviceHub devices (from backend)
 */

import type { DeviceTemplate, DeviceHubDevice } from '~/types/device'
import { DEFAULT_DEVICE_TEMPLATES, DEVICE_COLORS } from '~/types/device'

const props = defineProps<{
  deviceHubDevices?: DeviceHubDevice[]
}>()

const emit = defineEmits<{
  (e: 'open-device-hub-dialog'): void
}>()

// Organize templates by class
const titanNativeTemplates = computed(() =>
  DEFAULT_DEVICE_TEMPLATES.filter(t => t.device_class === 'titan_native')
)

const thirdPartyTemplates = computed(() =>
  DEFAULT_DEVICE_TEMPLATES.filter(t => t.device_class === 'third_party')
)

// Section expansion state
const titanNativeExpanded = ref(true)
const thirdPartyExpanded = ref(true)

// Get icon for device type
function getDeviceIcon(deviceType: string): string {
  const icons: Record<string, string> = {
    pipetter: '💧',
    dispenser: '🧪',
    incubator: '🌡️',
    reader: '📊',
    washer: '🚿',
    centrifuge: '🌀',
    labeler: '🏷️',
    sealer: '📦',
    peeler: '📤',
    lidmate: '🔲',
    decapper: '🔓',
    hotel: '🏨',
    barcode_reader: '📱',
    robot: '🤖'
  }
  return icons[deviceType] || '📦'
}

// Get device color
function getDeviceColor(deviceType: string): string {
  return DEVICE_COLORS[deviceType as keyof typeof DEVICE_COLORS] || '#6b7280'
}

// Handle drag start
function handleDragStart(e: DragEvent, template: DeviceTemplate) {
  if (!e.dataTransfer) return

  e.dataTransfer.setData('application/json', JSON.stringify(template))
  e.dataTransfer.effectAllowed = 'copy'

  // Create custom drag image
  const dragEl = document.createElement('div')
  dragEl.className = 'drag-ghost'
  dragEl.style.cssText = `
    position: absolute;
    top: -1000px;
    padding: 8px 12px;
    background: ${getDeviceColor(template.device_type)};
    color: white;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
  `
  dragEl.textContent = template.name
  document.body.appendChild(dragEl)
  e.dataTransfer.setDragImage(dragEl, 0, 0)

  // Clean up after drag
  setTimeout(() => dragEl.remove(), 0)
}
</script>

<template>
  <div class="device-palette">
    <div class="palette-header">
      <h3>Devices</h3>
    </div>

    <!-- Titan Native Section -->
    <div class="palette-section">
      <h4
        class="section-header-collapsible"
        @click="titanNativeExpanded = !titanNativeExpanded"
      >
        <span class="expand-icon">{{ titanNativeExpanded ? '▼' : '▶' }}</span>
        Titan Native
        <span class="section-badge">{{ titanNativeTemplates.length }}</span>
      </h4>
      <div v-if="titanNativeExpanded" class="device-grid">
        <div
          v-for="template in titanNativeTemplates"
          :key="template.device_type"
          class="device-item"
          draggable="true"
          @dragstart="(e) => handleDragStart(e, template)"
        >
          <div
            class="device-icon"
            :style="{ backgroundColor: getDeviceColor(template.device_type) }"
          >
            {{ getDeviceIcon(template.device_type) }}
          </div>
          <span class="device-name">{{ template.name }}</span>
        </div>
      </div>
    </div>

    <!-- Third Party Section -->
    <div class="palette-section">
      <h4
        class="section-header-collapsible"
        @click="thirdPartyExpanded = !thirdPartyExpanded"
      >
        <span class="expand-icon">{{ thirdPartyExpanded ? '▼' : '▶' }}</span>
        Third Party
        <span class="section-badge">{{ thirdPartyTemplates.length }}</span>
      </h4>
      <div v-if="thirdPartyExpanded" class="device-grid">
        <div
          v-for="template in thirdPartyTemplates"
          :key="template.device_type"
          class="device-item"
          draggable="true"
          @dragstart="(e) => handleDragStart(e, template)"
        >
          <div
            class="device-icon"
            :style="{ backgroundColor: getDeviceColor(template.device_type) }"
          >
            {{ getDeviceIcon(template.device_type) }}
          </div>
          <span class="device-name">{{ template.name }}</span>
        </div>
      </div>
    </div>

    <!-- DeviceHub Section -->
    <div class="palette-section">
      <button
        class="btn btn-secondary btn-full"
        @click="emit('open-device-hub-dialog')"
      >
        <span class="btn-icon">+</span>
        Add from DeviceHub
      </button>
    </div>

    <!-- Help text -->
    <div class="palette-help">
      <p>Drag devices to the canvas to place them.</p>
      <p><strong>Titan Native:</strong> Snap to tile edges</p>
      <p><strong>Third Party:</strong> Free placement</p>
    </div>
  </div>
</template>

<style scoped>
.device-palette {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.palette-header {
  margin-bottom: 15px;
}

.palette-header h3 {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #3498db;
  margin: 0;
}

.palette-section {
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #34495e;
}

.palette-section:last-of-type {
  border-bottom: none;
}

.section-header-collapsible {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #bdc3c7;
  cursor: pointer;
  user-select: none;
  margin: 0 0 10px 0;
}

.section-header-collapsible:hover {
  color: white;
}

.expand-icon {
  font-size: 10px;
  color: #95a5a6;
  width: 12px;
}

.section-badge {
  background: #34495e;
  color: #95a5a6;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
  margin-left: auto;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.device-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: #34495e;
  border-radius: 4px;
  cursor: grab;
  transition: all 0.15s ease;
}

.device-item:hover {
  background: #3d566e;
  transform: translateY(-1px);
}

.device-item:active {
  cursor: grabbing;
  transform: translateY(0);
}

.device-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: 18px;
}

.device-name {
  font-size: 10px;
  color: #bdc3c7;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary {
  background: #34495e;
  color: #bdc3c7;
}

.btn-secondary:hover {
  background: #3d566e;
  color: white;
}

.btn-full {
  width: 100%;
}

.btn-icon {
  font-size: 14px;
  font-weight: bold;
}

.palette-help {
  margin-top: 10px;
  padding: 10px;
  background: rgba(52, 73, 94, 0.5);
  border-radius: 4px;
}

.palette-help p {
  font-size: 10px;
  color: #95a5a6;
  margin: 0 0 4px 0;
}

.palette-help p:last-child {
  margin-bottom: 0;
}

.palette-help strong {
  color: #bdc3c7;
}
</style>
