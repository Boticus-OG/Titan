<script setup lang="ts">
/**
 * DeckEditor - Visual deck configuration tool
 *
 * Features:
 * - Toggle tiles on/off for device placement
 * - Draw track lines with start/end points
 * - Snap-to-grid (5mm) and snap-to-quadrant-lines (60mm/180mm)
 * - Place waypoints, pivots, and queue points
 * - Real-time mover position overlay
 */

import type {
  DeckConfig,
  Track,
  Location,
  MoverState,
  StatorTile,
  EditorMode,
  EditorTool,
  DrawingTrack,
} from '~/types/deck'

const props = defineProps<{
  deck: DeckConfig
  movers: MoverState[]
}>()

const emit = defineEmits<{
  (e: 'tile-toggle', col: number, row: number, enabled: boolean): void
  (e: 'track-created', track: Partial<Track>): void
  (e: 'track-deleted', trackId: number): void
  (e: 'location-created', location: Partial<Location>): void
  (e: 'location-updated', locationId: string, x: number, y: number): void
  (e: 'location-deleted', locationId: string): void
}>()

// Visualization constants
const PIXELS_PER_MM = 0.5
const PADDING = 40
const TILE_SIZE = 240
const QUADRANT_OFFSETS = [60, 180]

// Editor state
const editorState = reactive({
  mode: 'view' as EditorMode,
  selectedTool: null as EditorTool | null,
  snapToGrid: true,
  snapDistance: 5,
  showQuadrantLines: true,
  showTracks: true,
  showQueuePoints: true,
  showLocations: true,
})

// Selection state
const selectedTrackId = ref<number | null>(null)
const selectedLocationId = ref<string | null>(null)
const selectedMoverId = ref<string | null>(null)

// Track drawing state
const isDrawingTrack = ref(false)
const drawingTrack = ref<DrawingTrack>({ start: null, current: null })

// Mouse position
const mousePos = ref<{ x: number; y: number } | null>(null)

// Computed dimensions
const viewWidth = computed(() => {
  if (!props.deck) return 400
  return props.deck.width_mm * PIXELS_PER_MM + PADDING * 2
})

const viewHeight = computed(() => {
  if (!props.deck) return 300
  return props.deck.height_mm * PIXELS_PER_MM + PADDING * 2
})

// Convert pixels to mm
function pixelsToMm(pixels: number): number {
  return (pixels - PADDING) / PIXELS_PER_MM
}

// Convert mm to pixels
function mmToPixels(mm: number): number {
  return mm * PIXELS_PER_MM + PADDING
}

// Snap position to grid or quadrant lines
function snapPosition(x: number, y: number): { x: number; y: number } {
  if (!editorState.snapToGrid) return { x, y }

  // Try to snap to quadrant points first (higher priority)
  const tileX = Math.floor(x / TILE_SIZE) * TILE_SIZE
  const tileY = Math.floor(y / TILE_SIZE) * TILE_SIZE

  for (const qx of QUADRANT_OFFSETS) {
    for (const qy of QUADRANT_OFFSETS) {
      const px = tileX + qx
      const py = tileY + qy
      const dist = Math.sqrt((x - px) ** 2 + (y - py) ** 2)
      if (dist <= 10) {
        return { x: px, y: py }
      }
    }
  }

  // Fall back to grid snap
  const snapDist = editorState.snapDistance
  return {
    x: Math.round(x / snapDist) * snapDist,
    y: Math.round(y / snapDist) * snapDist,
  }
}

// Get position from mouse event
function getEventPosition(event: MouseEvent): { x: number; y: number } {
  const svg = event.currentTarget as SVGElement
  const rect = svg.getBoundingClientRect()
  const x = pixelsToMm(event.clientX - rect.left)
  const y = pixelsToMm(event.clientY - rect.top)
  return snapPosition(x, y)
}

// Handle canvas click based on current mode
function handleCanvasClick(event: MouseEvent) {
  const pos = getEventPosition(event)

  switch (editorState.mode) {
    case 'draw_track':
      handleTrackClick(pos)
      break
    case 'place_location':
      handleLocationClick(pos)
      break
  }
}

// Handle tile click (for edit_tiles mode)
function handleTileClick(tile: StatorTile) {
  if (editorState.mode === 'edit_tiles') {
    emit('tile-toggle', tile.grid_pos.col, tile.grid_pos.row, !tile.enabled)
  }
}

// Handle track drawing click
function handleTrackClick(pos: { x: number; y: number }) {
  if (!isDrawingTrack.value) {
    // Start new track
    drawingTrack.value = { start: pos, current: pos }
    isDrawingTrack.value = true
  } else {
    // End track
    if (drawingTrack.value.start) {
      emit('track-created', {
        start_x: drawingTrack.value.start.x,
        start_y: drawingTrack.value.start.y,
        end_x: pos.x,
        end_y: pos.y,
        name: `Track ${(props.deck.tracks?.length || 0) + 1}`,
      })
    }
    drawingTrack.value = { start: null, current: null }
    isDrawingTrack.value = false
  }
}

// Handle location placement click
function handleLocationClick(pos: { x: number; y: number }) {
  const locationType = editorState.selectedTool === 'place_waypoint' ? 'waypoint'
    : editorState.selectedTool === 'place_device' ? 'device'
    : editorState.selectedTool === 'place_queue' ? 'queue'
    : 'device'

  emit('location-created', {
    name: `New ${locationType}`,
    location_type: locationType,
    x: pos.x,
    y: pos.y,
    c: 0,
  })
}

// Handle mouse move
function handleMouseMove(event: MouseEvent) {
  mousePos.value = getEventPosition(event)

  if (isDrawingTrack.value && drawingTrack.value.start) {
    drawingTrack.value.current = mousePos.value
  }
}

// Handle track selection
function handleTrackClick2(track: Track) {
  if (editorState.mode === 'view') {
    selectedTrackId.value = track.track_id
    selectedLocationId.value = null
    selectedMoverId.value = null
  }
}

// Handle location selection
function handleLocationClick2(location: Location) {
  selectedLocationId.value = location.location_id
  selectedTrackId.value = null
  selectedMoverId.value = null
}

// Handle mover selection
function handleMoverClick(mover: MoverState) {
  selectedMoverId.value = mover.actor_id
  selectedTrackId.value = null
  selectedLocationId.value = null
}

// Handle location move
function handleLocationMoved(locationId: string, x: number, y: number) {
  emit('location-updated', locationId, x, y)
}

// Set editor mode
function setMode(mode: EditorMode) {
  editorState.mode = mode
  // Reset drawing state when changing modes
  if (mode !== 'draw_track') {
    isDrawingTrack.value = false
    drawingTrack.value = { start: null, current: null }
  }
}

// Cancel current operation (Escape key)
function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    if (isDrawingTrack.value) {
      isDrawingTrack.value = false
      drawingTrack.value = { start: null, current: null }
    }
    editorState.mode = 'view'
  }
  // Delete selected track
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedTrackId.value !== null) {
      emit('track-deleted', selectedTrackId.value)
      selectedTrackId.value = null
    }
    if (selectedLocationId.value !== null) {
      emit('location-deleted', selectedLocationId.value)
      selectedLocationId.value = null
    }
  }
}

// Set up keyboard listeners
onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div class="deck-editor" tabindex="0">
    <!-- Toolbar -->
    <div class="editor-toolbar">
      <div class="toolbar-section">
        <span class="toolbar-label">Mode:</span>
        <button
          :class="{ active: editorState.mode === 'view' }"
          @click="setMode('view')"
        >
          View
        </button>
        <button
          :class="{ active: editorState.mode === 'edit_tiles' }"
          @click="setMode('edit_tiles')"
        >
          Edit Tiles
        </button>
        <button
          :class="{ active: editorState.mode === 'draw_track' }"
          @click="setMode('draw_track')"
        >
          Draw Track
        </button>
        <button
          :class="{ active: editorState.mode === 'place_location' }"
          @click="setMode('place_location'); editorState.selectedTool = 'place_waypoint'"
        >
          Place Location
        </button>
      </div>

      <div v-if="editorState.mode === 'place_location'" class="toolbar-section">
        <span class="toolbar-label">Type:</span>
        <button
          :class="{ active: editorState.selectedTool === 'place_waypoint' }"
          @click="editorState.selectedTool = 'place_waypoint'"
        >
          Waypoint
        </button>
        <button
          :class="{ active: editorState.selectedTool === 'place_device' }"
          @click="editorState.selectedTool = 'place_device'"
        >
          Device
        </button>
        <button
          :class="{ active: editorState.selectedTool === 'place_queue' }"
          @click="editorState.selectedTool = 'place_queue'"
        >
          Queue
        </button>
      </div>

      <div class="toolbar-separator" />

      <div class="toolbar-section toolbar-toggles">
        <label>
          <input v-model="editorState.snapToGrid" type="checkbox" />
          Snap
        </label>
        <label>
          <input v-model="editorState.showQuadrantLines" type="checkbox" />
          Quadrants
        </label>
        <label>
          <input v-model="editorState.showTracks" type="checkbox" />
          Tracks
        </label>
        <label>
          <input v-model="editorState.showLocations" type="checkbox" />
          Locations
        </label>
      </div>

      <div class="toolbar-spacer" />

      <!-- Mouse position display -->
      <div v-if="mousePos" class="mouse-position">
        X: {{ mousePos.x.toFixed(1) }}mm, Y: {{ mousePos.y.toFixed(1) }}mm
      </div>
    </div>

    <!-- Canvas -->
    <div class="editor-canvas-container">
      <svg
        :width="viewWidth"
        :height="viewHeight"
        class="editor-canvas"
        @click="handleCanvasClick"
        @mousemove="handleMouseMove"
      >
        <!-- Background -->
        <rect
          x="0"
          y="0"
          :width="viewWidth"
          :height="viewHeight"
          fill="#0f0f0f"
        />

        <!-- Deck Grid -->
        <DeckGrid
          :deck="deck"
          :show-quadrant-lines="editorState.showQuadrantLines"
          :pixels-per-mm="PIXELS_PER_MM"
          :padding="PADDING"
          @tile-click="handleTileClick"
        />

        <!-- Stations (from existing DeckView logic) -->
        <g class="stations">
          <g
            v-for="station in deck.stations"
            :key="station.station_id"
            class="station"
          >
            <rect
              :x="mmToPixels(station.position.x) - (TILE_SIZE * PIXELS_PER_MM)/2 + 8"
              :y="mmToPixels(station.position.y) - (TILE_SIZE * PIXELS_PER_MM)/2 + 8"
              :width="(TILE_SIZE * PIXELS_PER_MM) - 16"
              :height="(TILE_SIZE * PIXELS_PER_MM) - 16"
              fill-opacity="0.3"
              stroke-width="2"
              rx="4"
              :fill="station.device_type === 'pipetter' ? '#8b5cf6' : station.device_type === 'dispenser' ? '#06b6d4' : station.device_type === 'incubator' ? '#f59e0b' : station.device_type === 'lidmate' ? '#ec4899' : '#888'"
              :stroke="station.device_type === 'pipetter' ? '#8b5cf6' : station.device_type === 'dispenser' ? '#06b6d4' : station.device_type === 'incubator' ? '#f59e0b' : station.device_type === 'lidmate' ? '#ec4899' : '#888'"
            />
            <text
              :x="mmToPixels(station.position.x)"
              :y="mmToPixels(station.position.y)"
              text-anchor="middle"
              dominant-baseline="middle"
              fill="white"
              font-size="11"
              font-weight="600"
            >
              {{ station.name }}
            </text>
          </g>
        </g>

        <!-- Tracks Layer -->
        <TrackLayer
          v-if="editorState.showTracks && deck.tracks"
          :tracks="deck.tracks"
          :drawing-track="isDrawingTrack ? drawingTrack : null"
          :pixels-per-mm="PIXELS_PER_MM"
          :padding="PADDING"
          :selected-track-id="selectedTrackId"
          @track-click="handleTrackClick2"
        />

        <!-- Locations Layer -->
        <LocationLayer
          v-if="editorState.showLocations && deck.locations"
          :locations="deck.locations"
          :pixels-per-mm="PIXELS_PER_MM"
          :padding="PADDING"
          :editable="editorState.mode === 'place_location'"
          :selected-location-id="selectedLocationId"
          @location-click="handleLocationClick2"
          @location-moved="handleLocationMoved"
        />

        <!-- Movers Layer (always on top) -->
        <MoverLayer
          :movers="movers"
          :pixels-per-mm="PIXELS_PER_MM"
          :padding="PADDING"
          :selected-mover-id="selectedMoverId"
          @mover-click="handleMoverClick"
        />
      </svg>
    </div>

    <!-- Status bar -->
    <div class="editor-status">
      <span>{{ deck.cols }}x{{ deck.rows }} grid ({{ deck.width_mm }}mm x {{ deck.height_mm }}mm)</span>
      <span v-if="editorState.mode === 'draw_track' && isDrawingTrack">
        Click to place track end point. Press Escape to cancel.
      </span>
      <span v-else-if="editorState.mode === 'draw_track'">
        Click to place track start point.
      </span>
      <span v-else-if="editorState.mode === 'edit_tiles'">
        Click tiles to toggle enabled/disabled.
      </span>
      <span v-else-if="editorState.mode === 'place_location'">
        Click to place {{ editorState.selectedTool?.replace('place_', '') }}.
      </span>
    </div>
  </div>
</template>

<style scoped>
.deck-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  outline: none;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.toolbar-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-right: var(--space-1);
}

.toolbar-separator {
  width: 1px;
  height: 24px;
  background: var(--color-border);
}

.toolbar-spacer {
  flex: 1;
}

.toolbar-toggles label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.toolbar-toggles input {
  cursor: pointer;
}

.editor-toolbar button {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-elevated);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.editor-toolbar button:hover {
  background: var(--color-surface-hover);
}

.editor-toolbar button.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.mouse-position {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  background: var(--color-surface-elevated);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.editor-canvas-container {
  flex: 1;
  overflow: auto;
  background: #1a1a1a;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: var(--space-4);
}

.editor-canvas {
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3));
  cursor: crosshair;
}

.editor-status {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
</style>
