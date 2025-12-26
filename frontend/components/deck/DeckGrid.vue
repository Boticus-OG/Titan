<script setup lang="ts">
/**
 * DeckGrid - Renders stator tiles with quadrant reference lines
 *
 * Quadrant points are at 60mm and 180mm within each tile (from TrackDesigner)
 */

import type { DeckConfig, StatorTile } from '~/types/deck'

const props = defineProps<{
  deck: DeckConfig
  showQuadrantLines: boolean
  pixelsPerMm: number
  padding: number
}>()

const emit = defineEmits<{
  (e: 'tile-click', tile: StatorTile): void
}>()

// Constants
const TILE_SIZE = 240
const QUADRANT_OFFSETS = [60, 180]

// Compute quadrant points for a tile
function getQuadrantPoints(tile: StatorTile) {
  return QUADRANT_OFFSETS.flatMap((qx) =>
    QUADRANT_OFFSETS.map((qy) => ({
      x: tile.bounds[0] + qx,
      y: tile.bounds[1] + qy,
      key: `${qx}-${qy}`,
    }))
  )
}

// Convert mm to pixels
function mmToPixels(mm: number): number {
  return mm * props.pixelsPerMm + props.padding
}

// Get tile fill color
function getTileFill(tile: StatorTile): string {
  return tile.enabled ? '#1e293b' : '#e67e22'
}

// Get tile stroke color
function getTileStroke(tile: StatorTile): string {
  return tile.enabled ? '#334155' : '#d35400'
}
</script>

<template>
  <g class="deck-grid">
    <!-- Stator Tiles -->
    <g
      v-for="tile in deck.tiles"
      :key="`tile-${tile.grid_pos.col}-${tile.grid_pos.row}`"
      class="tile"
      :class="{ disabled: !tile.enabled }"
      @click="emit('tile-click', tile)"
    >
      <!-- Tile background -->
      <rect
        :x="mmToPixels(tile.bounds[0])"
        :y="mmToPixels(tile.bounds[1])"
        :width="TILE_SIZE * pixelsPerMm"
        :height="TILE_SIZE * pixelsPerMm"
        :fill="getTileFill(tile)"
        :stroke="getTileStroke(tile)"
        stroke-width="1"
      />

      <!-- Quadrant reference lines (only for enabled tiles) -->
      <g v-if="showQuadrantLines && tile.enabled" class="quadrant-lines">
        <!-- Vertical lines at 60mm and 180mm -->
        <line
          v-for="qx in QUADRANT_OFFSETS"
          :key="`vline-${qx}`"
          :x1="mmToPixels(tile.bounds[0] + qx)"
          :y1="mmToPixels(tile.bounds[1])"
          :x2="mmToPixels(tile.bounds[0] + qx)"
          :y2="mmToPixels(tile.bounds[3])"
          stroke="#475569"
          stroke-width="0.5"
          stroke-dasharray="2,2"
        />
        <!-- Horizontal lines at 60mm and 180mm -->
        <line
          v-for="qy in QUADRANT_OFFSETS"
          :key="`hline-${qy}`"
          :x1="mmToPixels(tile.bounds[0])"
          :y1="mmToPixels(tile.bounds[1] + qy)"
          :x2="mmToPixels(tile.bounds[2])"
          :y2="mmToPixels(tile.bounds[1] + qy)"
          stroke="#475569"
          stroke-width="0.5"
          stroke-dasharray="2,2"
        />
        <!-- Quadrant intersection points -->
        <circle
          v-for="qp in getQuadrantPoints(tile)"
          :key="`qp-${qp.key}`"
          :cx="mmToPixels(qp.x)"
          :cy="mmToPixels(qp.y)"
          r="2"
          fill="#64748b"
        />
        <!-- Center point (120mm, 120mm) -->
        <circle
          :cx="mmToPixels(tile.bounds[0] + 120)"
          :cy="mmToPixels(tile.bounds[1] + 120)"
          r="3"
          fill="#ef4444"
        />
      </g>

      <!-- Tile number (for disabled tiles, show dash) -->
      <text
        v-if="!tile.enabled"
        :x="mmToPixels(tile.bounds[0] + 120)"
        :y="mmToPixels(tile.bounds[1] + 120)"
        text-anchor="middle"
        dominant-baseline="middle"
        fill="white"
        font-size="16"
        font-weight="bold"
      >
        -
      </text>
    </g>

    <!-- Origin marker (0,0) -->
    <g class="origin-marker">
      <line
        :x1="mmToPixels(0)"
        :y1="mmToPixels(-10)"
        :x2="mmToPixels(0)"
        :y2="mmToPixels(20)"
        stroke="#ef4444"
        stroke-width="2"
      />
      <line
        :x1="mmToPixels(-10)"
        :y1="mmToPixels(0)"
        :x2="mmToPixels(20)"
        :y2="mmToPixels(0)"
        stroke="#ef4444"
        stroke-width="2"
      />
      <text
        :x="mmToPixels(-5)"
        :y="mmToPixels(-15)"
        fill="#ef4444"
        font-size="10"
        font-weight="bold"
      >
        (0,0)
      </text>
    </g>
  </g>
</template>

<style scoped>
.tile {
  cursor: pointer;
}

.tile:hover rect {
  filter: brightness(1.1);
}

.tile.disabled rect {
  cursor: not-allowed;
}

.quadrant-lines {
  pointer-events: none;
}
</style>
