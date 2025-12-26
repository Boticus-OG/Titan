<script setup lang="ts">
/**
 * LocationLayer - Renders location markers (waypoints, devices, pivots, queues)
 */

import type { Location, LocationType } from '~/types/deck'

const props = defineProps<{
  locations: Location[]
  pixelsPerMm: number
  padding: number
  editable: boolean
  selectedLocationId: string | null
}>()

const emit = defineEmits<{
  (e: 'location-click', location: Location): void
  (e: 'location-moved', locationId: string, x: number, y: number): void
}>()

// Convert mm to pixels
function mmToPixels(mm: number): number {
  return mm * props.pixelsPerMm + props.padding
}

// Location type colors
const typeColors: Record<LocationType, string> = {
  waypoint: '#22c55e',
  device: '#8b5cf6',
  pivot: '#f59e0b',
  queue: '#06b6d4',
  track_service_location: '#94a3b8',
}

// Location type icons (simplified shapes)
const typeIcons: Record<LocationType, string> = {
  waypoint: 'W',
  device: 'D',
  pivot: 'P',
  queue: 'Q',
  track_service_location: 'S',
}

// Get location color
function getColor(location: Location): string {
  return typeColors[location.location_type] || '#888'
}

// Get location icon
function getIcon(location: Location): string {
  return typeIcons[location.location_type] || '?'
}

// Check if selected
function isSelected(location: Location): boolean {
  return props.selectedLocationId === location.location_id
}

// Dragging state
const dragging = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })

function startDrag(event: MouseEvent, location: Location) {
  if (!props.editable) return
  dragging.value = location.location_id
  dragOffset.value = {
    x: event.clientX - mmToPixels(location.x),
    y: event.clientY - mmToPixels(location.y),
  }
}

function onDrag(event: MouseEvent) {
  if (!dragging.value || !props.editable) return

  const newX = (event.clientX - dragOffset.value.x - props.padding) / props.pixelsPerMm
  const newY = (event.clientY - dragOffset.value.y - props.padding) / props.pixelsPerMm

  emit('location-moved', dragging.value, newX, newY)
}

function endDrag() {
  dragging.value = null
}

// Attach global mouse handlers when dragging
watch(dragging, (val) => {
  if (val) {
    window.addEventListener('mousemove', onDrag)
    window.addEventListener('mouseup', endDrag)
  } else {
    window.removeEventListener('mousemove', onDrag)
    window.removeEventListener('mouseup', endDrag)
  }
})
</script>

<template>
  <g class="location-layer">
    <g
      v-for="location in locations"
      :key="location.location_id"
      class="location"
      :class="{
        selected: isSelected(location),
        draggable: editable,
        dragging: dragging === location.location_id,
      }"
      @click="emit('location-click', location)"
      @mousedown="startDrag($event, location)"
    >
      <!-- Location marker circle -->
      <circle
        :cx="mmToPixels(location.x)"
        :cy="mmToPixels(location.y)"
        r="12"
        :fill="getColor(location)"
        :stroke="isSelected(location) ? 'white' : 'transparent'"
        stroke-width="2"
      />

      <!-- Location type icon -->
      <text
        :x="mmToPixels(location.x)"
        :y="mmToPixels(location.y) + 4"
        text-anchor="middle"
        fill="white"
        font-size="10"
        font-weight="bold"
      >
        {{ getIcon(location) }}
      </text>

      <!-- Location name label (on hover or selected) -->
      <g
        v-if="isSelected(location)"
        class="location-label"
      >
        <rect
          :x="mmToPixels(location.x) - 40"
          :y="mmToPixels(location.y) - 28"
          width="80"
          height="16"
          rx="4"
          fill="rgba(0, 0, 0, 0.8)"
        />
        <text
          :x="mmToPixels(location.x)"
          :y="mmToPixels(location.y) - 16"
          text-anchor="middle"
          fill="white"
          font-size="9"
        >
          {{ location.name.length > 12 ? location.name.slice(0, 12) + '...' : location.name }}
        </text>
      </g>

      <!-- Rotation indicator (if rotation != 0) -->
      <line
        v-if="location.c !== 0"
        :x1="mmToPixels(location.x)"
        :y1="mmToPixels(location.y)"
        :x2="mmToPixels(location.x) + Math.cos(location.c * Math.PI / 180) * 15"
        :y2="mmToPixels(location.y) + Math.sin(location.c * Math.PI / 180) * 15"
        stroke="white"
        stroke-width="2"
      />
    </g>
  </g>
</template>

<style scoped>
.location {
  cursor: pointer;
}

.location:hover circle {
  filter: brightness(1.2);
}

.location.selected circle {
  filter: drop-shadow(0 0 4px white);
}

.location.draggable {
  cursor: grab;
}

.location.dragging {
  cursor: grabbing;
}

.location-label {
  pointer-events: none;
}
</style>
