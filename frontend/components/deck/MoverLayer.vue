<script setup lang="ts">
/**
 * MoverLayer - Real-time mover position visualization
 * Uses lower-left origin coordinate system
 */

import type { MoverState } from '~/types/deck'

const props = defineProps<{
  movers: MoverState[]
  pixelsPerMm: number
  padding: number
  maxY: number
  selectedMoverId: string | null
}>()

const emit = defineEmits<{
  (e: 'mover-click', mover: MoverState): void
}>()

// Convert mm to pixels (X axis - no inversion)
function mmToPixelsX(mm: number): number {
  return mm * props.pixelsPerMm + props.padding
}

// Convert mm to pixels (Y axis - inverted for lower-left origin)
function mmToPixelsY(mm: number): number {
  return (props.maxY - mm) * props.pixelsPerMm + props.padding
}

// Get mover X position
function getMoverX(mover: MoverState): number {
  return mmToPixelsX(mover.physical?.position?.x ?? 0)
}

// Get mover Y position
function getMoverY(mover: MoverState): number {
  return mmToPixelsY(mover.physical?.position?.y ?? 0)
}

// Get mover rotation (negate for Y-inversion)
function getMoverRotation(mover: MoverState): number {
  return -(mover.physical?.position?.c ?? 0)
}

// Get mover state
function getMoverStateStr(mover: MoverState): string {
  return mover.physical?.state ?? 'idle'
}

// Get mover color based on state
function getMoverColor(mover: MoverState): string {
  const state = getMoverStateStr(mover)
  switch (state) {
    case 'idle':
      return 'var(--color-mover)'
    case 'assigned':
      return 'var(--color-plate)'
    case 'transporting':
      return 'var(--color-mover-active)'
    default:
      return '#94a3b8'
  }
}

// Check if selected
function isSelected(mover: MoverState): boolean {
  return props.selectedMoverId === mover.actor_id
}
</script>

<template>
  <g class="mover-layer">
    <g
      v-for="mover in movers"
      :key="mover.actor_id"
      class="mover"
      :class="{ selected: isSelected(mover) }"
      :transform="`rotate(${getMoverRotation(mover)}, ${getMoverX(mover)}, ${getMoverY(mover)})`"
      @click="emit('mover-click', mover)"
    >
      <!-- Mover body (square with rounded corners) -->
      <rect
        :x="getMoverX(mover) - 20"
        :y="getMoverY(mover) - 20"
        width="40"
        height="40"
        :fill="getMoverColor(mover)"
        rx="4"
        stroke="white"
        stroke-width="1"
      />

      <!-- Direction indicator (front of mover - points up in local coords) -->
      <polygon
        :points="`${getMoverX(mover)},${getMoverY(mover) - 25} ${getMoverX(mover) - 6},${getMoverY(mover) - 18} ${getMoverX(mover) + 6},${getMoverY(mover) - 18}`"
        fill="white"
      />

      <!-- Mover ID -->
      <text
        :x="getMoverX(mover)"
        :y="getMoverY(mover) + 5"
        text-anchor="middle"
        fill="#0f172a"
        font-size="14"
        font-weight="bold"
      >
        {{ mover.mover_id }}
      </text>

      <!-- Plate indicator (if carrying plate) -->
      <circle
        v-if="mover.assigned_plate_id"
        :cx="getMoverX(mover)"
        :cy="getMoverY(mover) - 32"
        r="8"
        fill="var(--color-plate)"
        stroke="white"
        stroke-width="1"
      >
        <animate
          attributeName="opacity"
          values="1;0.6;1"
          dur="1.5s"
          repeatCount="indefinite"
        />
      </circle>

      <!-- State label (on hover or selected) -->
      <g v-if="isSelected(mover)" class="mover-label">
        <rect
          :x="getMoverX(mover) - 35"
          :y="getMoverY(mover) + 26"
          width="70"
          height="16"
          rx="4"
          fill="rgba(0, 0, 0, 0.8)"
        />
        <text
          :x="getMoverX(mover)"
          :y="getMoverY(mover) + 38"
          text-anchor="middle"
          fill="white"
          font-size="9"
        >
          {{ getMoverStateStr(mover) }}
        </text>
      </g>

      <!-- Track position indicator (if on track) -->
      <g v-if="mover.physical?.track_id" class="track-indicator">
        <text
          :x="getMoverX(mover) + 24"
          :y="getMoverY(mover)"
          fill="#94a3b8"
          font-size="8"
        >
          T{{ mover.physical.track_id }}
        </text>
      </g>
    </g>
  </g>
</template>

<style scoped>
.mover {
  cursor: pointer;
  transition: transform 0.1s ease-out;
}

.mover:hover rect {
  filter: brightness(1.15);
}

.mover.selected rect {
  filter: drop-shadow(0 0 6px white);
  stroke-width: 2;
}

.mover-label {
  pointer-events: none;
}

.track-indicator {
  pointer-events: none;
}
</style>
