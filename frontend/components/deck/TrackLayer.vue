<script setup lang="ts">
/**
 * TrackLayer - Renders tracks and in-progress track drawing
 * Uses lower-left origin coordinate system
 */

import type { Track, DrawingTrack } from '~/types/deck'

const props = defineProps<{
  tracks: Track[]
  drawingTrack: DrawingTrack | null
  pixelsPerMm: number
  padding: number
  maxY: number
  selectedTrackId: number | null
}>()

const emit = defineEmits<{
  (e: 'track-click', track: Track): void
}>()

// Convert mm to pixels (X axis - no inversion)
function mmToPixelsX(mm: number): number {
  return mm * props.pixelsPerMm + props.padding
}

// Convert mm to pixels (Y axis - inverted for lower-left origin)
function mmToPixelsY(mm: number): number {
  return (props.maxY - mm) * props.pixelsPerMm + props.padding
}

// Check if track is selected
function isSelected(track: Track): boolean {
  return props.selectedTrackId === track.track_id
}

// Get track color
function getTrackColor(track: Track): string {
  return isSelected(track) ? 'var(--color-mover-active)' : 'var(--color-track)'
}
</script>

<template>
  <g class="track-layer">
    <!-- Existing tracks -->
    <g
      v-for="track in tracks"
      :key="`track-${track.track_id}`"
      class="track"
      :class="{ selected: isSelected(track) }"
      @click="emit('track-click', track)"
    >
      <!-- Track line -->
      <line
        :x1="mmToPixelsX(track.start_x)"
        :y1="mmToPixelsY(track.start_y)"
        :x2="mmToPixelsX(track.end_x)"
        :y2="mmToPixelsY(track.end_y)"
        :stroke="getTrackColor(track)"
        stroke-width="3"
        stroke-linecap="round"
      />

      <!-- Start point (green) -->
      <circle
        :cx="mmToPixelsX(track.start_x)"
        :cy="mmToPixelsY(track.start_y)"
        r="5"
        fill="var(--color-track-start)"
        stroke="white"
        stroke-width="1"
      />

      <!-- End point (red) -->
      <circle
        :cx="mmToPixelsX(track.end_x)"
        :cy="mmToPixelsY(track.end_y)"
        r="5"
        fill="var(--color-track-end)"
        stroke="white"
        stroke-width="1"
      />

      <!-- Track ID label at midpoint -->
      <g class="track-label">
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

    <!-- Drawing track (in progress) -->
    <g v-if="drawingTrack?.start" class="drawing-track">
      <!-- Line from start to current mouse position -->
      <line
        v-if="drawingTrack.current"
        :x1="mmToPixelsX(drawingTrack.start.x)"
        :y1="mmToPixelsY(drawingTrack.start.y)"
        :x2="mmToPixelsX(drawingTrack.current.x)"
        :y2="mmToPixelsY(drawingTrack.current.y)"
        stroke="var(--color-plate)"
        stroke-width="3"
        stroke-dasharray="5,5"
        stroke-linecap="round"
      />

      <!-- Start point -->
      <circle
        :cx="mmToPixelsX(drawingTrack.start.x)"
        :cy="mmToPixelsY(drawingTrack.start.y)"
        r="6"
        fill="var(--color-track-start)"
        stroke="var(--color-plate)"
        stroke-width="2"
      >
        <animate
          attributeName="r"
          values="5;7;5"
          dur="1s"
          repeatCount="indefinite"
        />
      </circle>

      <!-- Current point indicator -->
      <circle
        v-if="drawingTrack.current"
        :cx="mmToPixelsX(drawingTrack.current.x)"
        :cy="mmToPixelsY(drawingTrack.current.y)"
        r="4"
        fill="var(--color-plate)"
        opacity="0.8"
      />
    </g>
  </g>
</template>

<style scoped>
.track {
  cursor: pointer;
}

.track:hover line {
  stroke-width: 4;
}

.track.selected line {
  filter: drop-shadow(0 0 4px var(--color-mover-active));
}

.track-label {
  pointer-events: none;
}

.drawing-track {
  pointer-events: none;
}
</style>
