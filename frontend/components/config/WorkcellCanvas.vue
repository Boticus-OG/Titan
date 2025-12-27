<script setup lang="ts">
/**
 * WorkcellCanvas - Main canvas for system configuration
 *
 * Features:
 * - Infinite canvas with pan/zoom (boundless)
 * - Deck tiles visualization
 * - Device rendering with drag-and-drop
 * - Tile edge snapping for native devices
 * - Smooth rotation with 90-degree snaps
 */

import type { DeckConfig, MoverState } from '~/types/deck'
import type { Device, DeviceTemplate, LayerVisibility } from '~/types/device'
import { TILE_SIZE_MM, MIN_ZOOM, MAX_ZOOM, DEVICE_COLORS } from '~/types/device'

const props = defineProps<{
  deck: DeckConfig | null
  devices: Device[]
  movers: MoverState[]
  selectedDeviceId: string | null
  zoom: number
  panX: number
  panY: number
  layers: LayerVisibility
  isDragging: boolean
}>()

const emit = defineEmits<{
  (e: 'update:zoom', zoom: number): void
  (e: 'update:panX', panX: number): void
  (e: 'update:panY', panY: number): void
  (e: 'select-device', deviceId: string | null): void
  (e: 'move-device', deviceId: string, position: { x: number; y: number }): void
  (e: 'move-device-end', deviceId: string, position: { x: number; y: number }): void
  (e: 'rotate-device', deviceId: string, angle: number): void
  (e: 'drop-device', template: DeviceTemplate, position: { x: number; y: number }): void
  (e: 'canvas-click', position: { x: number; y: number }): void
}>()

// Refs
const canvasContainer = ref<HTMLDivElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)

// Local state
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const draggedDeviceId = ref<string | null>(null)
const dragStartPos = ref({ x: 0, y: 0 })
const deviceDragOffset = ref({ x: 0, y: 0 })
const mousePos = ref({ x: 0, y: 0 })

// Rotation state
const isRotating = ref(false)
const rotatingDeviceId = ref<string | null>(null)
const rotationStartAngle = ref(0)
const rotationCenterPos = ref({ x: 0, y: 0 })
const currentRotationAngle = ref(0)

// Computed
const viewBox = computed(() => {
  if (!canvasContainer.value) return '0 0 1000 800'
  const rect = canvasContainer.value.getBoundingClientRect()
  const width = rect.width / props.zoom
  const height = rect.height / props.zoom
  const x = -props.panX / props.zoom
  const y = -props.panY / props.zoom
  return `${x} ${y} ${width} ${height}`
})

const deckHeight = computed(() => props.deck?.height_mm || 720)

// Convert screen coordinates to canvas coordinates
function screenToCanvas(screenX: number, screenY: number): { x: number; y: number } {
  if (!canvasContainer.value) return { x: 0, y: 0 }
  const rect = canvasContainer.value.getBoundingClientRect()
  return {
    x: (screenX - rect.left - props.panX) / props.zoom,
    y: (screenY - rect.top - props.panY) / props.zoom
  }
}

// Snap position to tile edge for native devices
function snapToTileEdge(pos: { x: number; y: number }, device: Device): { x: number; y: number } {
  if (device.device_class !== 'titan_native' || !props.deck) {
    return pos
  }

  // Find the nearest tile edge
  // Native devices sit adjacent to the deck with overhang over a tile
  const tileX = Math.round(pos.x / TILE_SIZE_MM) * TILE_SIZE_MM
  const tileY = Math.round(pos.y / TILE_SIZE_MM) * TILE_SIZE_MM

  // Determine which edge based on orientation
  // 0° = device above tile, overhang extends down
  // 90° = device to right of tile, overhang extends left
  // 180° = device below tile, overhang extends up
  // 270° = device to left of tile, overhang extends right

  const orientation = device.orientation || 0

  switch (orientation) {
    case 0: // Device above, overhang down
      return { x: tileX, y: tileY - TILE_SIZE_MM }
    case 90: // Device to right, overhang left
      return { x: tileX + TILE_SIZE_MM, y: tileY }
    case 180: // Device below, overhang up
      return { x: tileX, y: tileY + TILE_SIZE_MM }
    case 270: // Device to left, overhang right
      return { x: tileX - TILE_SIZE_MM, y: tileY }
    default:
      return { x: tileX, y: tileY }
  }
}

// Get tile color based on state
function getTileColor(tile: { enabled: boolean }): string {
  return tile.enabled ? '#34495e' : '#e67e22'
}

// Get device color
function getDeviceColor(device: Device): string {
  return DEVICE_COLORS[device.device_type] || '#6b7280'
}

// Calculate overhang position based on device orientation
function getOverhangPosition(device: Device): { x: number; y: number; width: number; height: number } | null {
  if (!device.overhang) return null

  const bodySize = TILE_SIZE_MM // Native devices are 240x240
  const ohWidth = device.overhang.width
  const ohDepth = device.overhang.depth
  const orientation = device.orientation || 0

  // Overhang extends from the device body toward the tile
  // The overhang is centered on the edge it extends from
  switch (orientation) {
    case 0: // Overhang extends down from bottom of body
      return {
        x: device.position.x + (bodySize - ohWidth) / 2,
        y: device.position.y + bodySize,
        width: ohWidth,
        height: ohDepth
      }
    case 90: // Overhang extends left from left side of body
      return {
        x: device.position.x - ohDepth,
        y: device.position.y + (bodySize - ohWidth) / 2,
        width: ohDepth,
        height: ohWidth
      }
    case 180: // Overhang extends up from top of body
      return {
        x: device.position.x + (bodySize - ohWidth) / 2,
        y: device.position.y - ohDepth,
        width: ohWidth,
        height: ohDepth
      }
    case 270: // Overhang extends right from right side of body
      return {
        x: device.position.x + bodySize,
        y: device.position.y + (bodySize - ohWidth) / 2,
        width: ohDepth,
        height: ohWidth
      }
    default:
      return {
        x: device.position.x + (bodySize - ohWidth) / 2,
        y: device.position.y + bodySize,
        width: ohWidth,
        height: ohDepth
      }
  }
}

// Calculate nest position based on device orientation
function getNestPosition(device: Device): { x: number; y: number } {
  const bodySize = device.footprint.width // Should be 240 for native
  const orientation = device.orientation || 0

  // Nest is in the overhang area, centered
  if (device.overhang) {
    const ohDepth = device.overhang.depth
    switch (orientation) {
      case 0: // Nest below body
        return {
          x: device.position.x + bodySize / 2,
          y: device.position.y + bodySize + ohDepth / 2
        }
      case 90: // Nest to left of body
        return {
          x: device.position.x - ohDepth / 2,
          y: device.position.y + bodySize / 2
        }
      case 180: // Nest above body
        return {
          x: device.position.x + bodySize / 2,
          y: device.position.y - ohDepth / 2
        }
      case 270: // Nest to right of body
        return {
          x: device.position.x + bodySize + ohDepth / 2,
          y: device.position.y + bodySize / 2
        }
    }
  }

  // For third-party devices, nest is inside body
  return {
    x: device.position.x + device.nest.x,
    y: device.position.y + device.nest.y
  }
}

// Get selection box dimensions (includes overhang)
function getSelectionBox(device: Device): { x: number; y: number; width: number; height: number } {
  const bodySize = device.footprint.width
  const orientation = device.orientation || 0
  const ohDepth = device.overhang?.depth || 0

  let x = device.position.x
  let y = device.position.y
  let width = bodySize
  let height = bodySize

  if (device.overhang) {
    switch (orientation) {
      case 0: // Overhang below
        height = bodySize + ohDepth
        break
      case 90: // Overhang to left
        x = device.position.x - ohDepth
        width = bodySize + ohDepth
        break
      case 180: // Overhang above
        y = device.position.y - ohDepth
        height = bodySize + ohDepth
        break
      case 270: // Overhang to right
        width = bodySize + ohDepth
        break
    }
  }

  return { x: x - 4, y: y - 4, width: width + 8, height: height + 8 }
}

// Get rotation handle position
function getRotationHandlePosition(device: Device): { lineX1: number; lineY1: number; lineX2: number; lineY2: number; cx: number; cy: number } {
  const box = getSelectionBox(device)
  const centerY = box.y + 4 + (box.height - 8) / 2

  return {
    lineX1: box.x + box.width,
    lineY1: centerY,
    lineX2: box.x + box.width + 20,
    lineY2: centerY,
    cx: box.x + box.width + 26,
    cy: centerY
  }
}

// Event handlers
function handleWheel(e: WheelEvent) {
  e.preventDefault()

  if (!canvasContainer.value) return
  const rect = canvasContainer.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9
  const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, props.zoom * zoomFactor))

  const zoomRatio = newZoom / props.zoom
  const newPanX = mouseX - (mouseX - props.panX) * zoomRatio
  const newPanY = mouseY - (mouseY - props.panY) * zoomRatio

  emit('update:zoom', newZoom)
  emit('update:panX', newPanX)
  emit('update:panY', newPanY)
}

function handleMouseDown(e: MouseEvent) {
  // Right-click or middle-click for panning
  if (e.button === 1 || e.button === 2) {
    e.preventDefault()
    isPanning.value = true
    panStart.value = { x: e.clientX - props.panX, y: e.clientY - props.panY }
    return
  }

  // Left-click - check if clicking on canvas background
  const target = e.target as SVGElement
  if (target === svgRef.value || target.classList.contains('canvas-background')) {
    emit('select-device', null)
    const pos = screenToCanvas(e.clientX, e.clientY)
    emit('canvas-click', pos)
  }
}

function handleMouseMove(e: MouseEvent) {
  mousePos.value = screenToCanvas(e.clientX, e.clientY)

  if (isPanning.value) {
    emit('update:panX', e.clientX - panStart.value.x)
    emit('update:panY', e.clientY - panStart.value.y)
    return
  }

  // Handle rotation dragging
  if (isRotating.value && rotatingDeviceId.value) {
    const pos = screenToCanvas(e.clientX, e.clientY)

    // Calculate angle from center to mouse
    const dx = pos.x - rotationCenterPos.value.x
    const dy = pos.y - rotationCenterPos.value.y
    let angle = Math.atan2(dy, dx) * (180 / Math.PI)

    // Snap to 90-degree increments
    angle = Math.round(angle / 90) * 90

    // Normalize to 0, 90, 180, 270
    angle = ((angle % 360) + 360) % 360
    if (angle > 270) angle = 0

    currentRotationAngle.value = angle
    return
  }

  if (draggedDeviceId.value) {
    const pos = screenToCanvas(e.clientX, e.clientY)
    const device = props.devices.find(d => d.device_id === draggedDeviceId.value)
    if (device) {
      let newPos = {
        x: pos.x - deviceDragOffset.value.x,
        y: pos.y - deviceDragOffset.value.y
      }
      // Snap for native devices
      if (device.device_class === 'titan_native') {
        newPos = snapToTileEdge(newPos, device)
      }
      emit('move-device', draggedDeviceId.value, newPos)
    }
  }
}

function handleMouseUp(e: MouseEvent) {
  if (isPanning.value) {
    isPanning.value = false
    return
  }

  // Handle rotation end
  if (isRotating.value && rotatingDeviceId.value) {
    emit('rotate-device', rotatingDeviceId.value, currentRotationAngle.value)
    isRotating.value = false
    rotatingDeviceId.value = null
    return
  }

  if (draggedDeviceId.value) {
    const pos = screenToCanvas(e.clientX, e.clientY)
    const device = props.devices.find(d => d.device_id === draggedDeviceId.value)
    if (device) {
      let newPos = {
        x: pos.x - deviceDragOffset.value.x,
        y: pos.y - deviceDragOffset.value.y
      }
      // Snap for native devices
      if (device.device_class === 'titan_native') {
        newPos = snapToTileEdge(newPos, device)
      }
      emit('move-device-end', draggedDeviceId.value, newPos)
    }
    draggedDeviceId.value = null
  }
}

function handleContextMenu(e: MouseEvent) {
  e.preventDefault()
}

// Device interaction
function handleDeviceMouseDown(e: MouseEvent, device: Device) {
  e.stopPropagation()

  if (e.button !== 0) return  // Only left-click

  emit('select-device', device.device_id)

  // Start dragging
  const pos = screenToCanvas(e.clientX, e.clientY)
  draggedDeviceId.value = device.device_id
  dragStartPos.value = { x: device.position.x, y: device.position.y }
  deviceDragOffset.value = {
    x: pos.x - device.position.x,
    y: pos.y - device.position.y
  }
}

// Rotation handle - start drag rotation
function handleRotationMouseDown(e: MouseEvent, device: Device) {
  e.stopPropagation()
  e.preventDefault()

  isRotating.value = true
  rotatingDeviceId.value = device.device_id
  rotationStartAngle.value = device.orientation || 0
  currentRotationAngle.value = device.orientation || 0

  // Calculate device center for rotation
  const bodySize = device.footprint.width
  rotationCenterPos.value = {
    x: device.position.x + bodySize / 2,
    y: device.position.y + bodySize / 2
  }
}

// Drag and drop from palette
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy'
  }
}

function handleDrop(e: DragEvent) {
  e.preventDefault()

  if (!e.dataTransfer) return

  try {
    const templateData = e.dataTransfer.getData('application/json')
    if (!templateData) return

    const template = JSON.parse(templateData) as DeviceTemplate
    const pos = screenToCanvas(e.clientX, e.clientY)

    // For native devices, snap to tile grid
    let dropPos = {
      x: pos.x - template.default_footprint.width / 2,
      y: pos.y - template.default_footprint.height / 2
    }

    if (template.device_class === 'titan_native') {
      // Snap to tile grid
      dropPos = {
        x: Math.round(dropPos.x / TILE_SIZE_MM) * TILE_SIZE_MM,
        y: Math.round(dropPos.y / TILE_SIZE_MM) * TILE_SIZE_MM
      }
    }

    emit('drop-device', template, dropPos)
  } catch (err) {
    console.error('Failed to parse dropped device template:', err)
  }
}

// Lifecycle
onMounted(() => {
  if (canvasContainer.value) {
    canvasContainer.value.addEventListener('wheel', handleWheel, { passive: false })
  }
})

onUnmounted(() => {
  if (canvasContainer.value) {
    canvasContainer.value.removeEventListener('wheel', handleWheel)
  }
})
</script>

<template>
  <div
    ref="canvasContainer"
    class="workcell-canvas"
    @mousedown="handleMouseDown"
    @mousemove="handleMouseMove"
    @mouseup="handleMouseUp"
    @mouseleave="handleMouseUp"
    @contextmenu="handleContextMenu"
    @dragover="handleDragOver"
    @drop="handleDrop"
  >
    <svg
      ref="svgRef"
      class="canvas-svg"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- Background -->
      <rect
        class="canvas-background"
        x="-10000"
        y="-10000"
        width="20000"
        height="20000"
        fill="white"
      />

      <!-- Grid pattern for reference -->
      <defs>
        <pattern
          id="grid-small"
          width="60"
          height="60"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 60 0 L 0 0 0 60"
            fill="none"
            stroke="#f0f0f0"
            stroke-width="0.5"
          />
        </pattern>
      </defs>

      <!-- Reference grid -->
      <rect
        x="-2000"
        y="-2000"
        width="6000"
        height="6000"
        fill="url(#grid-small)"
      />

      <!-- Stator Tiles Layer -->
      <g v-if="layers.tiles && deck" class="tiles-layer">
        <rect
          v-for="(tile, i) in deck.tiles"
          :key="'tile-' + i"
          :x="tile.bounds[0]"
          :y="deckHeight - tile.bounds[3]"
          :width="TILE_SIZE_MM"
          :height="TILE_SIZE_MM"
          :fill="getTileColor(tile)"
          stroke="#2c3e50"
          stroke-width="2"
        />
      </g>

      <!-- Tracks Layer -->
      <g v-if="layers.tracks && deck?.tracks" class="tracks-layer">
        <line
          v-for="(track, i) in deck.tracks"
          :key="'track-' + i"
          :x1="track.start_x"
          :y1="deckHeight - track.start_y"
          :x2="track.end_x"
          :y2="deckHeight - track.end_y"
          stroke="#27ae60"
          stroke-width="3"
        />
      </g>

      <!-- Devices Layer -->
      <g v-if="layers.devices" class="devices-layer">
        <g
          v-for="device in devices"
          :key="device.device_id"
          class="device-group"
          :class="{ selected: device.device_id === selectedDeviceId, dragging: device.device_id === draggedDeviceId }"
          @mousedown="(e) => handleDeviceMouseDown(e, device)"
        >
          <!-- Device body (always square for native, no rotation transform) -->
          <rect
            :x="device.position.x"
            :y="device.position.y"
            :width="device.footprint.width"
            :height="device.footprint.height"
            :fill="getDeviceColor(device)"
            stroke="#2c3e50"
            stroke-width="2"
            rx="4"
          />

          <!-- Overhang (position changes based on orientation) -->
          <rect
            v-if="getOverhangPosition(device)"
            :x="getOverhangPosition(device)!.x"
            :y="getOverhangPosition(device)!.y"
            :width="getOverhangPosition(device)!.width"
            :height="getOverhangPosition(device)!.height"
            :fill="getDeviceColor(device)"
            fill-opacity="0.3"
            :stroke="getDeviceColor(device)"
            stroke-opacity="0.5"
            stroke-width="1"
            stroke-dasharray="4,2"
          />

          <!-- Nest marker (position changes based on orientation) -->
          <g class="nest-marker">
            <circle
              :cx="getNestPosition(device).x"
              :cy="getNestPosition(device).y"
              r="8"
              fill="none"
              :stroke="getDeviceColor(device)"
              stroke-width="2"
            />
            <circle
              :cx="getNestPosition(device).x"
              :cy="getNestPosition(device).y"
              r="3"
              :fill="getDeviceColor(device)"
            />
          </g>

          <!-- Orientation indicator (arrow showing direction) -->
          <g v-if="device.device_class === 'titan_native'" class="orientation-indicator">
            <path
              :d="(() => {
                const cx = device.position.x + device.footprint.width / 2
                const cy = device.position.y + device.footprint.height / 2
                const size = 20
                const orientation = device.orientation || 0
                // Arrow pointing in overhang direction
                switch (orientation) {
                  case 0: return `M ${cx} ${cy + 10} L ${cx - 8} ${cy - 5} L ${cx + 8} ${cy - 5} Z`
                  case 90: return `M ${cx - 10} ${cy} L ${cx + 5} ${cy - 8} L ${cx + 5} ${cy + 8} Z`
                  case 180: return `M ${cx} ${cy - 10} L ${cx - 8} ${cy + 5} L ${cx + 8} ${cy + 5} Z`
                  case 270: return `M ${cx + 10} ${cy} L ${cx - 5} ${cy - 8} L ${cx - 5} ${cy + 8} Z`
                  default: return `M ${cx} ${cy + 10} L ${cx - 8} ${cy - 5} L ${cx + 8} ${cy - 5} Z`
                }
              })()"
              fill="white"
              fill-opacity="0.8"
            />
          </g>

          <!-- Device label -->
          <text
            v-if="layers.labels"
            :x="device.position.x + device.footprint.width / 2"
            :y="device.position.y + device.footprint.height / 2 + 25"
            text-anchor="middle"
            dominant-baseline="middle"
            fill="white"
            font-size="12"
            font-weight="600"
            pointer-events="none"
          >
            {{ device.name }}
          </text>

          <!-- Selection indicator -->
          <rect
            v-if="device.device_id === selectedDeviceId"
            :x="getSelectionBox(device).x"
            :y="getSelectionBox(device).y"
            :width="getSelectionBox(device).width"
            :height="getSelectionBox(device).height"
            fill="none"
            stroke="#f39c12"
            stroke-width="2"
            stroke-dasharray="6,3"
            rx="4"
          />

          <!-- Rotation handle removed - use rotation buttons in properties panel -->
        </g>
      </g>

      <!-- Rotation preview removed - rotation now via properties panel -->

      <!-- Movers Layer -->
      <g v-if="layers.movers" class="movers-layer">
        <g
          v-for="mover in movers"
          :key="mover.actor_id"
          class="mover"
        >
          <rect
            :x="(mover.physical?.position?.x || 0) - 70"
            :y="deckHeight - (mover.physical?.position?.y || 0) - 59"
            width="140"
            height="118"
            :fill="mover.physical?.state === 'idle' ? '#60a5fa' : '#22d3ee'"
            rx="4"
          />
          <text
            :x="mover.physical?.position?.x || 0"
            :y="deckHeight - (mover.physical?.position?.y || 0)"
            text-anchor="middle"
            dominant-baseline="middle"
            fill="#0f0f0f"
            font-size="14"
            font-weight="700"
          >
            {{ mover.mover_id }}
          </text>
        </g>
      </g>
    </svg>

    <!-- Zoom controls overlay -->
    <div class="zoom-controls">
      <span class="zoom-level">{{ (zoom * 100).toFixed(0) }}%</span>
    </div>

    <!-- Mouse position overlay -->
    <div class="mouse-position">
      X: {{ mousePos.x.toFixed(0) }} Y: {{ mousePos.y.toFixed(0) }}
    </div>
  </div>
</template>

<style scoped>
.workcell-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: white;
  cursor: default;
}

.workcell-canvas:active {
  cursor: grabbing;
}

.canvas-svg {
  width: 100%;
  height: 100%;
}

.device-group {
  cursor: move;
}

.device-group:hover rect:first-child {
  filter: brightness(1.1);
}

.device-group.selected rect:first-child {
  filter: brightness(1.05);
}

.device-group.dragging {
  opacity: 0.8;
}


.zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(44, 62, 80, 0.9);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.mouse-position {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: rgba(44, 62, 80, 0.9);
  color: #bdc3c7;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
}

.mover {
  pointer-events: none;
}
</style>
