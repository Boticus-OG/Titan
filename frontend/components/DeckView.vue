<script setup lang="ts">
/**
 * DeckView - 2D Top-Down Visualization of XPlanar Deck
 * Shows tiles, stations, tracks, and movers with layer controls
 */

import type { DeckConfig, MoverState, PlateState, Station, Track } from '~/types/deck'

// Layer visibility state
const layers = reactive({
  tiles: true,
  stations: true,
  tracks: true,
  movers: true,
  labels: true,
})

const props = defineProps<{
  deck: DeckConfig
  movers: MoverState[]
  plates: PlateState[]
}>()

const emit = defineEmits<{
  (e: 'select-station', station: Station): void
  (e: 'select-mover', mover: MoverState): void
}>()

// Visualization scaling - match Track Designer (1:1 scale)
const PIXELS_PER_MM = 1.0
const PADDING = 50

// Computed dimensions
const viewWidth = computed(() => {
  if (!props.deck) return 400
  return props.deck.width_mm * PIXELS_PER_MM + PADDING * 2
})

const viewHeight = computed(() => {
  if (!props.deck) return 300
  return props.deck.height_mm * PIXELS_PER_MM + PADDING * 2
})

const tileSize = computed(() => {
  if (!props.deck) return 120
  return props.deck.tile_size_mm * PIXELS_PER_MM
})

// Convert mm to pixels (X axis - left to right)
function mmToPixelsX(mm: number): number {
  return mm * PIXELS_PER_MM + PADDING
}

// Convert mm to pixels (Y axis - FLIPPED for lower-left origin like Track Designer)
function mmToPixelsY(mm: number): number {
  if (!props.deck) return PADDING
  // Flip Y: origin at bottom-left, Y increases upward
  return (props.deck.height_mm - mm) * PIXELS_PER_MM + PADDING
}

// Legacy function for tile bounds (uses top-left for X, but Y needs flipping)
function tileBoundsToPixels(bounds: [number, number, number, number]): { x: number, y: number } {
  // bounds = [x_min, y_min, x_max, y_max]
  // We want top-left corner of the visual rect, but with Y flipped
  // So we use x_min for X, but for Y we need to flip y_max (which becomes visual top)
  return {
    x: bounds[0] * PIXELS_PER_MM + PADDING,
    y: (props.deck.height_mm - bounds[3]) * PIXELS_PER_MM + PADDING
  }
}

// Get station color
function getStationColor(deviceType: string): string {
  const colors: Record<string, string> = {
    pipetter: '#8b5cf6',
    dispenser: '#06b6d4',
    incubator: '#f59e0b',
    lidmate: '#ec4899',
  }
  return colors[deviceType] || '#888'
}

// Get mover position safely (with Y flipped for lower-left origin)
function getMoverX(mover: MoverState): number {
  return mmToPixelsX(mover.physical?.position?.x ?? 0)
}

function getMoverY(mover: MoverState): number {
  return mmToPixelsY(mover.physical?.position?.y ?? 0)
}

function getMoverState(mover: MoverState): string {
  return mover.physical?.state ?? 'idle'
}

// Expose layers for parent component control
defineExpose({
  layers
})
</script>

<template>
  <div class="deck-container">
    <svg
      :width="viewWidth"
      :height="viewHeight"
      class="deck-svg"
    >
      <!-- Stator Tiles (Y-flipped for lower-left origin) - TD style colors -->
      <g v-if="layers.tiles" class="tiles">
        <rect
          v-for="(tile, i) in deck.tiles"
          :key="'tile-' + i"
          :x="tileBoundsToPixels(tile.bounds).x"
          :y="tileBoundsToPixels(tile.bounds).y"
          :width="tileSize"
          :height="tileSize"
          :fill="tile.enabled ? '#34495e' : '#e67e22'"
          stroke="#2c3e50"
          stroke-width="2"
        />
      </g>

      <!-- Stations (Y-flipped for lower-left origin) -->
      <g v-if="layers.stations" class="stations">
        <g
          v-for="(station, i) in deck.stations"
          :key="'station-' + i"
          class="station"
          style="cursor: pointer"
          @click="emit('select-station', station)"
        >
          <rect
            :x="mmToPixelsX(station.position.x) - tileSize/2 + 8"
            :y="mmToPixelsY(station.position.y) - tileSize/2 + 8"
            :width="tileSize - 16"
            :height="tileSize - 16"
            :fill="getStationColor(station.device_type)"
            fill-opacity="0.3"
            :stroke="getStationColor(station.device_type)"
            stroke-width="2"
            rx="4"
          />
          <text
            v-if="layers.labels"
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

      <!-- Tracks (Y-flipped for lower-left origin) -->
      <g v-if="layers.tracks && deck.tracks" class="tracks">
        <g
          v-for="track in deck.tracks"
          :key="'track-' + track.track_id"
          class="track"
        >
          <!-- Track line -->
          <line
            :x1="mmToPixelsX(track.start_x)"
            :y1="mmToPixelsY(track.start_y)"
            :x2="mmToPixelsX(track.end_x)"
            :y2="mmToPixelsY(track.end_y)"
            stroke="#22d3ee"
            stroke-width="3"
            stroke-linecap="round"
          />
          <!-- Start point (green) -->
          <circle
            :cx="mmToPixelsX(track.start_x)"
            :cy="mmToPixelsY(track.start_y)"
            r="5"
            fill="#22c55e"
            stroke="white"
            stroke-width="1"
          />
          <!-- End point (red) -->
          <circle
            :cx="mmToPixelsX(track.end_x)"
            :cy="mmToPixelsY(track.end_y)"
            r="5"
            fill="#ef4444"
            stroke="white"
            stroke-width="1"
          />
          <!-- Track ID label at midpoint -->
          <g v-if="layers.labels" class="track-label">
            <rect
              :x="mmToPixelsX((track.start_x + track.end_x) / 2) - 12"
              :y="mmToPixelsY((track.start_y + track.end_y) / 2) - 8"
              width="24"
              height="16"
              rx="4"
              fill="rgba(0, 0, 0, 0.7)"
            />
            <text
              :x="mmToPixelsX((track.start_x + track.end_x) / 2)"
              :y="mmToPixelsY((track.start_y + track.end_y) / 2) + 4"
              text-anchor="middle"
              fill="white"
              font-size="10"
              font-weight="bold"
            >
              {{ track.track_id }}
            </text>
          </g>
        </g>
      </g>

      <!-- Movers -->
      <g v-if="layers.movers" class="movers">
        <g
          v-for="mover in movers"
          :key="mover.actor_id"
          class="mover"
          style="cursor: pointer"
          @click="emit('select-mover', mover)"
        >
          <rect
            :x="getMoverX(mover) - 20"
            :y="getMoverY(mover) - 20"
            width="40"
            height="40"
            :fill="getMoverState(mover) === 'idle' ? '#60a5fa' : '#22d3ee'"
            rx="4"
          />
          <text
            v-if="layers.labels"
            :x="getMoverX(mover)"
            :y="getMoverY(mover) + 4"
            text-anchor="middle"
            fill="#0f0f0f"
            font-size="14"
            font-weight="700"
          >
            {{ mover.mover_id }}
          </text>
          <!-- Plate indicator -->
          <circle
            v-if="mover.assigned_plate_id"
            :cx="getMoverX(mover)"
            :cy="getMoverY(mover) - 30"
            r="10"
            fill="#fbbf24"
          />
        </g>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.deck-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: auto;
}

.deck-svg {
  /* No shadow - clean look like TD */
}

.station:hover rect {
  fill-opacity: 0.5;
}

.mover:hover rect {
  filter: brightness(1.2);
}

.track line {
  filter: drop-shadow(0 0 2px rgba(34, 211, 238, 0.5));
}

.track-label {
  pointer-events: none;
}
</style>
