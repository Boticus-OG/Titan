<script setup lang="ts">
/**
 * DeckView - 2D Top-Down Visualization of XPlanar Deck
 * Simplified version for debugging
 */

import type { DeckConfig, MoverState, PlateState, Station } from '~/types/deck'

const props = defineProps<{
  deck: DeckConfig
  movers: MoverState[]
  plates: PlateState[]
}>()

const emit = defineEmits<{
  (e: 'select-station', station: Station): void
  (e: 'select-mover', mover: MoverState): void
}>()

// Visualization scaling
const PIXELS_PER_MM = 0.5
const PADDING = 40

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

// Convert mm to pixels
function mmToPixels(mm: number): number {
  return mm * PIXELS_PER_MM + PADDING
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

// Get mover position safely
function getMoverX(mover: MoverState): number {
  return mmToPixels(mover.physical?.position?.x ?? 0)
}

function getMoverY(mover: MoverState): number {
  return mmToPixels(mover.physical?.position?.y ?? 0)
}

function getMoverState(mover: MoverState): string {
  return mover.physical?.state ?? 'idle'
}
</script>

<template>
  <div class="deck-container">
    <svg
      :width="viewWidth"
      :height="viewHeight"
      class="deck-svg"
    >
      <!-- Background -->
      <rect
        x="0"
        y="0"
        :width="viewWidth"
        :height="viewHeight"
        fill="#0f0f0f"
      />

      <!-- Stator Tiles -->
      <g class="tiles">
        <rect
          v-for="(tile, i) in deck.tiles"
          :key="'tile-' + i"
          :x="mmToPixels(tile.bounds[0])"
          :y="mmToPixels(tile.bounds[1])"
          :width="tileSize"
          :height="tileSize"
          :fill="tile.enabled ? '#1e293b' : '#0c0c0c'"
          stroke="#334155"
          stroke-width="1"
        />
      </g>

      <!-- Stations -->
      <g class="stations">
        <g
          v-for="(station, i) in deck.stations"
          :key="'station-' + i"
          class="station"
          style="cursor: pointer"
          @click="emit('select-station', station)"
        >
          <rect
            :x="mmToPixels(station.position.x) - tileSize/2 + 8"
            :y="mmToPixels(station.position.y) - tileSize/2 + 8"
            :width="tileSize - 16"
            :height="tileSize - 16"
            :fill="getStationColor(station.device_type)"
            fill-opacity="0.3"
            :stroke="getStationColor(station.device_type)"
            stroke-width="2"
            rx="4"
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

      <!-- Movers -->
      <g class="movers">
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
  padding: 16px;
  background: #1a1a1a;
  border-radius: 12px;
  overflow: auto;
}

.deck-svg {
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3));
}

.station:hover rect {
  fill-opacity: 0.5;
}

.mover:hover rect {
  filter: brightness(1.2);
}
</style>
