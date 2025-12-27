<script setup lang="ts">
/**
 * DeviceProperties - Property editor for selected device
 *
 * Allows editing:
 * - Name
 * - Type
 * - Footprint dimensions
 * - Overhang dimensions
 * - Nest location
 * - Position
 * - Rotation
 */

import type { Device, DeviceType, Orientation } from '~/types/device'
import { DEVICE_COLORS } from '~/types/device'

const props = defineProps<{
  device: Device | null
}>()

const emit = defineEmits<{
  (e: 'update', updates: Partial<Device>): void
  (e: 'delete'): void
  (e: 'rotate', clockwise: boolean): void
}>()

// Device types for dropdown
const deviceTypes: { value: DeviceType; label: string }[] = [
  { value: 'pipetter', label: 'Pipetter' },
  { value: 'dispenser', label: 'Dispenser' },
  { value: 'incubator', label: 'Incubator' },
  { value: 'reader', label: 'Plate Reader' },
  { value: 'washer', label: 'Plate Washer' },
  { value: 'centrifuge', label: 'Centrifuge' },
  { value: 'labeler', label: 'Labeler' },
  { value: 'sealer', label: 'Sealer' },
  { value: 'peeler', label: 'Peeler' },
  { value: 'lidmate', label: 'Lid Handler' },
  { value: 'decapper', label: 'Decapper' },
  { value: 'hotel', label: 'Plate Hotel' },
  { value: 'barcode_reader', label: 'Barcode Reader' },
  { value: 'robot', label: 'Robot Arm' }
]

// A1 position options
const a1Positions: { value: Orientation; label: string }[] = [
  { value: 0, label: 'Upper-Left' },
  { value: 90, label: 'Upper-Right' },
  { value: 180, label: 'Lower-Right' },
  { value: 270, label: 'Lower-Left' }
]

// Section expansion state
const geometryExpanded = ref(true)
const nestExpanded = ref(true)
const positionExpanded = ref(true)

// Local editing state (to avoid direct mutation)
const localDevice = ref<Device | null>(null)

// Watch for device changes
watch(() => props.device, (newDevice) => {
  if (newDevice) {
    localDevice.value = JSON.parse(JSON.stringify(newDevice))
  } else {
    localDevice.value = null
  }
}, { immediate: true, deep: true })

// Emit updates
function emitUpdate(field: string, value: unknown) {
  if (!localDevice.value) return

  // Build nested update path
  const path = field.split('.')
  if (path.length === 1) {
    emit('update', { [field]: value })
  } else if (path.length === 2) {
    const [parent, child] = path
    const parentObj = localDevice.value[parent as keyof Device]
    if (typeof parentObj === 'object' && parentObj !== null) {
      emit('update', {
        [parent]: { ...parentObj, [child]: value }
      })
    }
  }
}

// Handle number input
function updateNumber(field: string, event: Event) {
  const target = event.target as HTMLInputElement
  const value = parseFloat(target.value) || 0
  emitUpdate(field, value)
}

// Handle text input
function updateText(field: string, event: Event) {
  const target = event.target as HTMLInputElement
  emitUpdate(field, target.value)
}

// Handle select
function updateSelect(field: string, event: Event) {
  const target = event.target as HTMLSelectElement
  emitUpdate(field, target.value)
}

// Confirm delete
function confirmDelete() {
  if (confirm('Delete this device?')) {
    emit('delete')
  }
}
</script>

<template>
  <div class="device-properties">
    <!-- No selection state -->
    <div v-if="!device" class="no-selection">
      <p class="text-muted">Select a device to edit its properties</p>
    </div>

    <!-- Device properties -->
    <div v-else class="properties-content">
      <!-- Header with device color -->
      <div
        class="properties-header"
        :style="{ borderLeftColor: DEVICE_COLORS[device.device_type] || '#6b7280' }"
      >
        <h3>{{ device.name }}</h3>
        <span class="device-class-badge" :class="device.device_class">
          {{ device.device_class === 'titan_native' ? 'Native' : 'Third Party' }}
        </span>
      </div>

      <!-- Basic info -->
      <div class="form-group">
        <label for="device-name">Name</label>
        <input
          id="device-name"
          type="text"
          :value="device.name"
          @input="(e) => updateText('name', e)"
        >
      </div>

      <div class="form-group">
        <label for="device-type">Type</label>
        <select
          id="device-type"
          :value="device.device_type"
          @change="(e) => updateSelect('device_type', e)"
        >
          <option
            v-for="dt in deviceTypes"
            :key="dt.value"
            :value="dt.value"
          >
            {{ dt.label }}
          </option>
        </select>
      </div>

      <!-- Geometry Section -->
      <div class="section">
        <h4
          class="section-header-collapsible"
          @click="geometryExpanded = !geometryExpanded"
        >
          <span class="expand-icon">{{ geometryExpanded ? '▼' : '▶' }}</span>
          Geometry
        </h4>

        <div v-if="geometryExpanded" class="section-content">
          <div class="form-row">
            <div class="form-group half">
              <label>Body Width (mm)</label>
              <input
                type="number"
                :value="device.footprint.width"
                @input="(e) => updateNumber('footprint.width', e)"
              >
            </div>
            <div class="form-group half">
              <label>Body Height (mm)</label>
              <input
                type="number"
                :value="device.footprint.height"
                @input="(e) => updateNumber('footprint.height', e)"
              >
            </div>
          </div>

          <template v-if="device.overhang">
            <div class="form-row">
              <div class="form-group half">
                <label>Overhang Width (mm)</label>
                <input
                  type="number"
                  :value="device.overhang.width"
                  @input="(e) => updateNumber('overhang.width', e)"
                >
              </div>
              <div class="form-group half">
                <label>Overhang Depth (mm)</label>
                <input
                  type="number"
                  :value="device.overhang.depth"
                  @input="(e) => updateNumber('overhang.depth', e)"
                >
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Nest Section -->
      <div class="section">
        <h4
          class="section-header-collapsible"
          @click="nestExpanded = !nestExpanded"
        >
          <span class="expand-icon">{{ nestExpanded ? '▼' : '▶' }}</span>
          Nest Location
        </h4>

        <div v-if="nestExpanded" class="section-content">
          <div class="form-row">
            <div class="form-group half">
              <label>Offset X (mm)</label>
              <input
                type="number"
                :value="device.nest.x"
                @input="(e) => updateNumber('nest.x', e)"
              >
            </div>
            <div class="form-group half">
              <label>Offset Y (mm)</label>
              <input
                type="number"
                :value="device.nest.y"
                @input="(e) => updateNumber('nest.y', e)"
              >
            </div>
          </div>

          <div class="form-group">
            <label>Expected A1 Position</label>
            <select
              :value="device.nest.expected_plate_orientation"
              @change="(e) => updateNumber('nest.expected_plate_orientation', e)"
            >
              <option
                v-for="pos in a1Positions"
                :key="pos.value"
                :value="pos.value"
              >
                {{ pos.label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Position Section -->
      <div class="section">
        <h4
          class="section-header-collapsible"
          @click="positionExpanded = !positionExpanded"
        >
          <span class="expand-icon">{{ positionExpanded ? '▼' : '▶' }}</span>
          Position
        </h4>

        <div v-if="positionExpanded" class="section-content">
          <div class="form-row">
            <div class="form-group half">
              <label>X (mm)</label>
              <input
                type="number"
                :value="device.position.x"
                step="5"
                @input="(e) => updateNumber('position.x', e)"
              >
            </div>
            <div class="form-group half">
              <label>Y (mm)</label>
              <input
                type="number"
                :value="device.position.y"
                step="5"
                @input="(e) => updateNumber('position.y', e)"
              >
            </div>
          </div>

          <div class="form-group">
            <label>Rotation</label>
            <div class="rotation-buttons">
              <button
                v-for="angle in [0, 90, 180, 270]"
                :key="angle"
                class="rotation-btn"
                :class="{ active: device.orientation === angle }"
                @click="emitUpdate('orientation', angle)"
              >
                {{ angle }}°
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Delete button -->
      <div class="section delete-section">
        <button class="btn btn-danger btn-full" @click="confirmDelete">
          Delete Device
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.device-properties {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.no-selection {
  padding: 15px 0;
  text-align: center;
}

.text-muted {
  color: #95a5a6;
  font-size: 12px;
}

.properties-content {
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
}

.properties-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid #34495e;
  border-left: 3px solid;
  padding-left: 6px;
}

.properties-header h3 {
  font-size: 12px;
  font-weight: 600;
  color: white;
  margin: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-class-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.device-class-badge.titan_native {
  background: rgba(52, 152, 219, 0.3);
  color: #3498db;
}

.device-class-badge.third_party {
  background: rgba(155, 89, 182, 0.3);
  color: #9b59b6;
}

.section {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #34495e;
}

.section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.section-header-collapsible {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  font-weight: 600;
  color: #bdc3c7;
  cursor: pointer;
  user-select: none;
  margin: 0 0 6px 0;
}

.section-header-collapsible:hover {
  color: white;
}

.expand-icon {
  font-size: 10px;
  color: #95a5a6;
  width: 12px;
}

.section-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.form-group label {
  font-size: 10px;
  color: #95a5a6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.form-group input,
.form-group select {
  background: #34495e;
  border: 1px solid #4a6278;
  color: white;
  padding: 4px 6px;
  border-radius: 3px;
  font-size: 11px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.form-group input[type="number"] {
  -moz-appearance: textfield;
}

.form-group input[type="number"]::-webkit-outer-spin-button,
.form-group input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #3498db;
}

.form-row {
  display: flex;
  gap: 4px;
}

.form-group.half {
  flex: 1;
  min-width: 0;
}

.rotation-buttons {
  display: flex;
  gap: 3px;
}

.rotation-btn {
  flex: 1;
  padding: 4px 2px;
  background: #34495e;
  border: 1px solid #4a6278;
  color: #bdc3c7;
  border-radius: 3px;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 0;
}

.rotation-btn:hover {
  background: #3d566e;
  color: white;
}

.rotation-btn.active {
  background: #3498db;
  border-color: #3498db;
  color: white;
}

.delete-section {
  margin-top: 8px;
  padding-top: 10px;
}

.btn {
  padding: 6px 10px;
  border: none;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-danger:hover {
  background: #c0392b;
}

.btn-full {
  width: 100%;
}
</style>
