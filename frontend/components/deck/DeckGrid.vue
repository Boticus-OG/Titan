<script setup lang="ts">
/**
 * DeckGrid - Renders stator tiles with quadrant reference lines
 *
 * Quadrant points are at 60mm and 180mm within each tile (from TrackDesigner)
 * Origin (0,0) is at lower-left corner
 * Tiles are numbered left-to-right, bottom-to-top
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

// Get the maximum Y for coordinate inversion (lower-left origin)
const maxY = computed(() => props.deck.height_mm)

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

// Convert mm to pixels with Y-axis inversion (lower-left origin)
function mmToPixelsX(mm: number): number {
  return mm * props.pixelsPerMm + props.padding
}

function mmToPixelsY(mm: number): number {
  // Invert Y: bottom (0) becomes top in SVG, top (maxY) becomes bottom
  return (maxY.value - mm) * props.pixelsPerMm + props.padding
}

// Get tile number (1-based, left-to-right, bottom-to-top)
function getTileNumber(tile: StatorTile): number {
  // Row 0 is at the bottom, so tile numbers start from bottom-left
  // Tile number = (row * cols) + col + 1
  const cols = props.deck.cols
  return tile.grid_pos.row * cols + tile.grid_pos.col + 1
}

// Get tile fill color
function getTileFill(tile: StatorTile): string {
  return tile.enabled ? 'var(--color-stator)' : 'var(--color-stator-disabled)'
}

// Get tile stroke color
function getTileStroke(tile: StatorTile): string {
  return tile.enabled ? 'var(--color-stator-border)' : 'var(--color-stator-disabled-border)'
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
        :x="mmToPixelsX(tile.bounds[0])"
        :y="mmToPixelsY(tile.bounds[3])"
        :width="TILE_SIZE * pixelsPerMm"
        :height="TILE_SIZE * pixelsPerMm"
        :fill="getTileFill(tile)"
        :stroke="getTileStroke(tile)"
        stroke-width="2"
      />

      <!-- Quadrant reference lines (only for enabled tiles) -->
      <g v-if="showQuadrantLines && tile.enabled" class="quadrant-lines">
        <!-- Vertical lines at 60mm and 180mm -->
        <line
          v-for="qx in QUADRANT_OFFSETS"
          :key="`vline-${qx}`"
          :x1="mmToPixelsX(tile.bounds[0] + qx)"
          :y1="mmToPixelsY(tile.bounds[3])"
          :x2="mmToPixelsX(tile.bounds[0] + qx)"
          :y2="mmToPixelsY(tile.bounds[1])"
          stroke="#475569"
          stroke-width="0.5"
          stroke-dasharray="2,2"
        />
        <!-- Horizontal lines at 60mm and 180mm -->
        <line
          v-for="qy in QUADRANT_OFFSETS"
          :key="`hline-${qy}`"
          :x1="mmToPixelsX(tile.bounds[0])"
          :y1="mmToPixelsY(tile.bounds[1] + qy)"
          :x2="mmToPixelsX(tile.bounds[2])"
          :y2="mmToPixelsY(tile.bounds[1] + qy)"
          stroke="#475569"
          stroke-width="0.5"
          stroke-dasharray="2,2"
        />
        <!-- Quadrant intersection points -->
        <circle
          v-for="qp in getQuadrantPoints(tile)"
          :key="`qp-${qp.key}`"
          :cx="mmToPixelsX(qp.x)"
          :cy="mmToPixelsY(qp.y)"
          r="2"
          fill="var(--color-quadrant)"
        />
        <!-- Quadrant crosshairs -->
        <g v-for="qp in getQuadrantPoints(tile)" :key="`qp-cross-${qp.key}`">
          <line
            :x1="mmToPixelsX(qp.x) - 4"
            :y1="mmToPixelsY(qp.y)"
            :x2="mmToPixelsX(qp.x) + 4"
            :y2="mmToPixelsY(qp.y)"
            stroke="var(--color-quadrant)"
            stroke-width="1"
          />
          <line
            :x1="mmToPixelsX(qp.x)"
            :y1="mmToPixelsY(qp.y) - 4"
            :x2="mmToPixelsX(qp.x)"
            :y2="mmToPixelsY(qp.y) + 4"
            stroke="var(--color-quadrant)"
            stroke-width="1"
          />
        </g>
        <!-- Center point (120mm, 120mm) -->
        <circle
          :cx="mmToPixelsX(tile.bounds[0] + 120)"
          :cy="mmToPixelsY(tile.bounds[1] + 120)"
          r="3"
          fill="var(--color-center)"
        />
        <!-- Center crosshair -->
        <line
          :x1="mmToPixelsX(tile.bounds[0] + 120) - 6"
          :y1="mmToPixelsY(tile.bounds[1] + 120)"
          :x2="mmToPixelsX(tile.bounds[0] + 120) + 6"
          :y2="mmToPixelsY(tile.bounds[1] + 120)"
          stroke="var(--color-center)"
          stroke-width="1"
        />
        <line
          :x1="mmToPixelsX(tile.bounds[0] + 120)"
          :y1="mmToPixelsY(tile.bounds[1] + 120) - 6"
          :x2="mmToPixelsX(tile.bounds[0] + 120)"
          :y2="mmToPixelsY(tile.bounds[1] + 120) + 6"
          stroke="var(--color-center)"
          stroke-width="1"
        />
      </g>

      <!-- Tile number label -->
      <text
        :x="mmToPixelsX(tile.bounds[0] + 120)"
        :y="mmToPixelsY(tile.bounds[1] + 120)"
        text-anchor="middle"
        dominant-baseline="middle"
        fill="white"
        font-size="16"
        font-weight="bold"
      >
        {{ tile.enabled ? `Tile ${getTileNumber(tile)}` : '—' }}
      </text>
    </g>

    <!-- Origin marker (0,0) at lower-left -->
    <g class="origin-marker">
      <!-- Horizontal axis (X) -->
      <line
        :x1="mmToPixelsX(-10)"
        :y1="mmToPixelsY(0)"
        :x2="mmToPixelsX(40)"
        :y2="mmToPixelsY(0)"
        stroke="var(--color-center)"
        stroke-width="3"
      />
      <!-- Vertical axis (Y) -->
      <line
        :x1="mmToPixelsX(0)"
        :y1="mmToPixelsY(-10)"
        :x2="mmToPixelsX(0)"
        :y2="mmToPixelsY(40)"
        stroke="var(--color-center)"
        stroke-width="3"
      />
      <!-- Origin label -->
      <text
        :x="mmToPixelsX(-5)"
        :y="mmToPixelsY(-20)"
        fill="var(--color-center)"
        font-size="14"
        font-weight="bold"
      >
        (0,0)
      </text>
      <!-- X label -->
      <text
        :x="mmToPixelsX(45)"
        :y="mmToPixelsY(-5)"
        fill="var(--color-center)"
        font-size="12"
        font-weight="bold"
      >
        X
      </text>
      <!-- Y label -->
      <text
        :x="mmToPixelsX(-15)"
        :y="mmToPixelsY(45)"
        fill="var(--color-center)"
        font-size="12"
        font-weight="bold"
      >
        Y
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
