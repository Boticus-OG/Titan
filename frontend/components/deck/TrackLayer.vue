<script setup lang="ts">
/**
 * TrackLayer - Renders tracks and in-progress track drawing
 */

import type { Track, DrawingTrack } from '~/types/deck'

const props = defineProps<{
  tracks: Track[]
  drawingTrack: DrawingTrack | null
  pixelsPerMm: number
  padding: number
  selectedTrackId: number | null
}>()

const emit = defineEmits<{
  (e: 'track-click', track: Track): void
}>()

// Convert mm to pixels
function mmToPixels(mm: number): number {
  return mm * props.pixelsPerMm + props.padding
}

// Check if track is selected
function isSelected(track: Track): boolean {
  return props.selectedTrackId === track.track_id
}

// Get track color
function getTrackColor(track: Track): string {
  return isSelected(track) ? '#22d3ee' : '#60a5fa'
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
        :x1="mmToPixels(track.start_x)"
        :y1="mmToPixels(track.start_y)"
        :x2="mmToPixels(track.end_x)"
        :y2="mmToPixels(track.end_y)"
        :stroke="getTrackColor(track)"
        stroke-width="3"
        stroke-linecap="round"
      />

      <!-- Start point (green) -->
      <circle
        :cx="mmToPixels(track.start_x)"
        :cy="mmToPixels(track.start_y)"
        r="5"
        fill="#22c55e"
        stroke="white"
        stroke-width="1"
      />

      <!-- End point (red) -->
      <circle
        :cx="mmToPixels(track.end_x)"
        :cy="mmToPixels(track.end_y)"
        r="5"
        fill="#ef4444"
        stroke="white"
        stroke-width="1"
      />

      <!-- Track ID label at midpoint -->
      <g class="track-label">
        <rect
          :x="mmToPixels((track.start_x + track.end_x) / 2) - 12"
          :y="mmToPixels((track.start_y + track.end_y) / 2) - 8"
          width="24"
          height="16"
          rx="4"
          fill="rgba(0, 0, 0, 0.7)"
        />
        <text
          :x="mmToPixels((track.start_x + track.end_x) / 2)"
          :y="mmToPixels((track.start_y + track.end_y) / 2) + 4"
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
        :x1="mmToPixels(drawingTrack.start.x)"
        :y1="mmToPixels(drawingTrack.start.y)"
        :x2="mmToPixels(drawingTrack.current.x)"
        :y2="mmToPixels(drawingTrack.current.y)"
        stroke="#fbbf24"
        stroke-width="3"
        stroke-dasharray="5,5"
        stroke-linecap="round"
      />

      <!-- Start point -->
      <circle
        :cx="mmToPixels(drawingTrack.start.x)"
        :cy="mmToPixels(drawingTrack.start.y)"
        r="6"
        fill="#22c55e"
        stroke="#fbbf24"
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
        :cx="mmToPixels(drawingTrack.current.x)"
        :cy="mmToPixels(drawingTrack.current.y)"
        r="4"
        fill="#fbbf24"
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
  filter: drop-shadow(0 0 4px #22d3ee);
}

.track-label {
  pointer-events: none;
}

.drawing-track {
  pointer-events: none;
}
</style>
