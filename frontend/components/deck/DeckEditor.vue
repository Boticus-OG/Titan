<script setup lang="ts">
/**
 * DeckEditor - Visual deck configuration tool (Track Designer style)
 *
 * Features:
 * - Toggle tiles on/off for device placement
 * - Draw track lines with start/end points
 * - Snap-to-grid (5mm) and snap-to-quadrant-lines (60mm/180mm)
 * - Place waypoints, pivots, and queue points
 * - Real-time mover position overlay
 * - Lower-left origin coordinate system
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
  (e: 'grid-resize', cols: number, rows: number): void
  (e: 'clear-tiles'): void
}>()

// Visualization constants
const PIXELS_PER_MM = 0.5
const PADDING = 50
const TILE_SIZE = 240
const QUADRANT_OFFSETS = [60, 180]

// Grid size inputs
const gridRows = ref(props.deck.rows)
const gridCols = ref(props.deck.cols)

// Watch for deck changes to update inputs
watch(() => props.deck, (newDeck) => {
  gridRows.value = newDeck.rows
  gridCols.value = newDeck.cols
}, { immediate: true })

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
  showCoordinates: false,
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

// Count of active tiles
const activeTileCount = computed(() => {
  return props.deck.tiles?.filter(t => t.enabled).length || 0
})

// Total tile count
const totalTileCount = computed(() => {
  return props.deck.tiles?.length || 0
})

// Get the maximum Y for coordinate inversion (lower-left origin)
const maxY = computed(() => props.deck.height_mm)

// Format coordinate with fixed width (5 digits, 2 decimals = "00000.00")
function formatCoord(value: number): string {
  return value.toFixed(2).padStart(8, ' ')
}

// Convert pixels to mm (with Y inversion for lower-left origin)
function pixelsToMmX(pixels: number): number {
  return (pixels - PADDING) / PIXELS_PER_MM
}

function pixelsToMmY(pixels: number): number {
  // Invert Y for lower-left origin
  return maxY.value - (pixels - PADDING) / PIXELS_PER_MM
}

// Convert mm to pixels (with Y inversion for lower-left origin)
function mmToPixelsX(mm: number): number {
  return mm * PIXELS_PER_MM + PADDING
}

function mmToPixelsY(mm: number): number {
  // Invert Y: bottom (0) becomes top in SVG, top (maxY) becomes bottom
  return (maxY.value - mm) * PIXELS_PER_MM + PADDING
}

// Legacy mmToPixels for components that don't need Y inversion
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

// Get position from mouse event (with Y inversion)
function getEventPosition(event: MouseEvent): { x: number; y: number } {
  const svg = event.currentTarget as SVGElement
  const rect = svg.getBoundingClientRect()
  const x = pixelsToMmX(event.clientX - rect.left)
  const y = pixelsToMmY(event.clientY - rect.top)
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
  // Toggle mode off if clicking same button
  if (editorState.mode === mode && mode !== 'view') {
    editorState.mode = 'view'
  } else {
    editorState.mode = mode
  }

  // Reset drawing state when changing modes
  if (editorState.mode !== 'draw_track') {
    isDrawingTrack.value = false
    drawingTrack.value = { start: null, current: null }
  }
}

// Create grid with specified dimensions
function createGrid() {
  emit('grid-resize', gridCols.value, gridRows.value)
}

// Clear all tiles
function clearTiles() {
  emit('clear-tiles')
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

// Get mode display text
const modeText = computed(() => {
  const modes: Record<string, string> = {
    'view': 'Select',
    'edit_tiles': 'Toggle Tile',
    'draw_track': 'Drawing Track',
    'place_location': 'Place Location',
  }
  return modes[editorState.mode] || 'Select'
})

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
    <div class="editor-layout">
      <!-- Sidebar -->
      <div class="editor-sidebar">
        <h2 class="sidebar-title">Titan Deck Editor</h2>

        <!-- Tile Layout Section -->
        <div class="section">
          <h3>Tile Layout</h3>
          <div class="grid-input">
            <label>Rows:</label>
            <input v-model.number="gridRows" type="number" min="1" max="20" />
          </div>
          <div class="grid-input">
            <label>Cols:</label>
            <input v-model.number="gridCols" type="number" min="1" max="20" />
          </div>
          <button class="btn btn-primary" @click="createGrid">Create Grid</button>
          <button class="btn btn-secondary" @click="clearTiles">Clear Tiles</button>
          <button
            class="btn"
            :class="{ active: editorState.mode === 'edit_tiles' }"
            @click="setMode('edit_tiles')"
          >
            Toggle Tile
          </button>

          <!-- Tile Legend -->
          <div class="legend">
            <div class="legend-title">Tile states:</div>
            <div class="legend-items">
              <div class="legend-item">
                <div class="legend-swatch" style="background: var(--color-stator);"></div>
                <span class="legend-label">Active Tile</span>
              </div>
              <div class="legend-item">
                <div class="legend-swatch" style="background: var(--color-stator-disabled);"></div>
                <span class="legend-label">Empty Space</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Track Drawing Section -->
        <div class="section">
          <h3>Track Drawing</h3>
          <button
            class="btn"
            :class="{ active: editorState.mode === 'draw_track' }"
            @click="setMode('draw_track')"
          >
            Draw Track
          </button>
          <button
            class="btn"
            :class="{ active: editorState.mode === 'place_location' }"
            @click="setMode('place_location'); editorState.selectedTool = 'place_waypoint'"
          >
            Place Location
          </button>
          <div style="margin-top: 10px;">
            <label style="display: flex; align-items: center; gap: 5px; cursor: pointer;">
              <input v-model="editorState.snapToGrid" type="checkbox" />
              Snap to Grid (5mm)
            </label>
          </div>
          <div style="margin-top: 5px;">
            <label style="display: flex; align-items: center; gap: 5px; cursor: pointer;">
              <input v-model="editorState.showCoordinates" type="checkbox" />
              Show Coordinates
            </label>
          </div>
        </div>

        <!-- Display Options Section -->
        <div class="section">
          <h3>Display Options</h3>
          <label style="display: flex; align-items: center; gap: 5px; cursor: pointer; margin-bottom: 5px;">
            <input v-model="editorState.showQuadrantLines" type="checkbox" />
            Show Quadrant Lines
          </label>
          <label style="display: flex; align-items: center; gap: 5px; cursor: pointer; margin-bottom: 5px;">
            <input v-model="editorState.showTracks" type="checkbox" />
            Show Tracks
          </label>
          <label style="display: flex; align-items: center; gap: 5px; cursor: pointer; margin-bottom: 5px;">
            <input v-model="editorState.showLocations" type="checkbox" />
            Show Locations
          </label>
        </div>
      </div>

      <!-- Main Area -->
      <div class="editor-main">
        <!-- Toolbar -->
        <div class="editor-toolbar toolbar">
          <span>Mode: <span class="mode-indicator">{{ modeText }}</span></span>
          <div class="toolbar-spacer" />
          <!-- Mouse position display with fixed width -->
          <div v-if="mousePos" class="mouse-position">
            X: {{ formatCoord(mousePos.x) }}mm, Y: {{ formatCoord(mousePos.y) }}mm
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
              fill="var(--color-canvas-bg)"
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
                  :x="mmToPixelsX(station.position.x) - (TILE_SIZE * PIXELS_PER_MM)/2 + 8"
                  :y="mmToPixelsY(station.position.y) - (TILE_SIZE * PIXELS_PER_MM)/2 + 8"
                  :width="(TILE_SIZE * PIXELS_PER_MM) - 16"
                  :height="(TILE_SIZE * PIXELS_PER_MM) - 16"
                  fill-opacity="0.3"
                  stroke-width="2"
                  rx="4"
                  :fill="station.device_type === 'pipetter' ? 'var(--color-station-pipetter)' : station.device_type === 'dispenser' ? 'var(--color-station-dispenser)' : station.device_type === 'incubator' ? 'var(--color-station-incubator)' : station.device_type === 'lidmate' ? 'var(--color-station-lidmate)' : '#888'"
                  :stroke="station.device_type === 'pipetter' ? 'var(--color-station-pipetter)' : station.device_type === 'dispenser' ? 'var(--color-station-dispenser)' : station.device_type === 'incubator' ? 'var(--color-station-incubator)' : station.device_type === 'lidmate' ? 'var(--color-station-lidmate)' : '#888'"
                />
                <text
                  :x="mmToPixelsX(station.position.x)"
                  :y="mmToPixelsY(station.position.y)"
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
              :max-y="maxY"
              :selected-track-id="selectedTrackId"
              @track-click="handleTrackClick2"
            />

            <!-- Locations Layer -->
            <LocationLayer
              v-if="editorState.showLocations && deck.locations"
              :locations="deck.locations"
              :pixels-per-mm="PIXELS_PER_MM"
              :padding="PADDING"
              :max-y="maxY"
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
              :max-y="maxY"
              :selected-mover-id="selectedMoverId"
              @mover-click="handleMoverClick"
            />
          </svg>
        </div>

        <!-- Status bar -->
        <div class="editor-status">
          <span>{{ deck.cols }}x{{ deck.rows }} grid • {{ activeTileCount }}/{{ totalTileCount }} active tiles • {{ deck.width_mm }}mm x {{ deck.height_mm }}mm</span>
          <span v-if="editorState.mode === 'draw_track' && isDrawingTrack">
            Click to place track end point. Press Escape to cancel.
          </span>
          <span v-else-if="editorState.mode === 'draw_track'">
            Click to place track start point.
          </span>
          <span v-else-if="editorState.mode === 'edit_tiles'">
            Click tiles to toggle between active/empty.
          </span>
          <span v-else-if="editorState.mode === 'place_location'">
            Click to place {{ editorState.selectedTool?.replace('place_', '') }}.
          </span>
          <span v-else>
            Select mode - Click on elements to select them.
          </span>
        </div>
      </div>
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

.editor-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.editor-sidebar {
  width: 320px;
  min-width: 250px;
  max-width: 500px;
  flex-shrink: 0;
  background: var(--color-surface);
  color: white;
  padding: 20px;
  overflow-y: auto;
  resize: horizontal;
  position: relative;
}

.editor-sidebar::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: var(--color-surface-elevated);
  cursor: ew-resize;
}

.sidebar-title {
  margin-bottom: 20px;
  color: var(--color-accent);
  font-size: 18px;
}

.editor-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface-elevated);
  color: white;
  flex-wrap: wrap;
}

.toolbar-spacer {
  flex: 1;
}

.mouse-position {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  min-width: 240px;
  text-align: right;
}

.editor-canvas-container {
  flex: 1;
  overflow: auto;
  background: var(--color-canvas-bg);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: var(--space-4);
}

.editor-canvas {
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.2));
  cursor: crosshair;
}

.editor-status {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  border-top: 1px solid var(--color-surface-elevated);
  font-size: var(--text-xs);
  color: white;
}
</style>
