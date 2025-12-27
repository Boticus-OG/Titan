/**
 * Device Manager Composable
 *
 * Manages device state for the System Configuration Tool.
 * - CRUD operations for devices
 * - Undo/redo support
 * - Canvas transform state
 * - Layer visibility
 */

import type {
  Device,
  DeviceTemplate,
  DeviceType,
  DeviceClass,
  Orientation,
  LayerVisibility,
  DeviceHubDevice
} from '~/types/device'
import {
  TILE_SIZE_MM,
  DEFAULT_OVERHANG_DEPTH,
  MIN_ZOOM,
  MAX_ZOOM,
  DEVICE_COLORS
} from '~/types/device'

// Generate unique ID
function generateId(): string {
  return `dev_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
}

export function useDeviceManager() {
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBase || ''

  // Device state
  const devices = ref<Device[]>([])
  const selectedDeviceId = ref<string | null>(null)

  // Undo/redo stacks
  const undoStack = ref<Device[][]>([])
  const redoStack = ref<Device[][]>([])
  const maxUndoDepth = 100

  // Canvas transform
  const zoom = ref(1.0)
  const panX = ref(0)
  const panY = ref(0)

  // Layer visibility
  const layers = ref<LayerVisibility>({
    tiles: true,
    devices: true,
    tracks: true,
    teachPoints: false,
    movers: true,
    labels: true
  })

  // Drag state
  const isDragging = ref(false)
  const dragOffset = ref<{ x: number; y: number } | null>(null)

  // Loading state
  const loading = ref(false)
  const error = ref<string | null>(null)
  const isDirty = ref(false)

  // Auto-save debounce timer
  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
  const AUTO_SAVE_DELAY = 1500 // 1.5 seconds after last change

  // Computed
  const selectedDevice = computed(() => {
    if (!selectedDeviceId.value) return null
    return devices.value.find(d => d.device_id === selectedDeviceId.value) || null
  })

  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)

  // Schedule auto-save with debounce
  function scheduleAutoSave() {
    isDirty.value = true
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
    }
    autoSaveTimer = setTimeout(async () => {
      if (isDirty.value && devices.value.length >= 0) {
        await saveDevicesInternal()
      }
    }, AUTO_SAVE_DELAY)
  }

  // Internal save (used by auto-save)
  async function saveDevicesInternal() {
    if (!isDirty.value) return
    try {
      await $fetch(`${baseUrl}/api/config/devices`, {
        method: 'PUT',
        body: devices.value
      })
      isDirty.value = false
      console.log('Auto-saved devices')
    } catch (e: unknown) {
      console.error('Auto-save failed:', e)
      // Don't clear dirty flag so next attempt will retry
    }
  }

  // Save state for undo
  function saveState() {
    const snapshot = JSON.parse(JSON.stringify(devices.value))
    undoStack.value.push(snapshot)
    if (undoStack.value.length > maxUndoDepth) {
      undoStack.value.shift()
    }
    // Clear redo stack when new action is performed
    redoStack.value = []
    // Schedule auto-save
    scheduleAutoSave()
  }

  // Undo last action
  function undo() {
    if (!canUndo.value) return

    const currentState = JSON.parse(JSON.stringify(devices.value))
    redoStack.value.push(currentState)

    const previousState = undoStack.value.pop()!
    devices.value = previousState

    // Clear selection if device no longer exists
    if (selectedDeviceId.value) {
      const exists = devices.value.find(d => d.device_id === selectedDeviceId.value)
      if (!exists) {
        selectedDeviceId.value = null
      }
    }

    // Schedule auto-save after undo
    scheduleAutoSave()
  }

  // Redo last undone action
  function redo() {
    if (!canRedo.value) return

    const currentState = JSON.parse(JSON.stringify(devices.value))
    undoStack.value.push(currentState)

    const nextState = redoStack.value.pop()!
    devices.value = nextState

    // Schedule auto-save after redo
    scheduleAutoSave()
  }

  // Add device from template
  function addDevice(template: DeviceTemplate, position: { x: number; y: number }): Device {
    saveState()

    const device: Device = {
      device_id: generateId(),
      name: template.name,
      device_type: template.device_type,
      device_class: template.device_class,
      footprint: { ...template.default_footprint },
      position: { ...position },
      orientation: 0,
      nest: {
        x: template.default_footprint.width / 2,
        y: template.default_footprint.height / 2,
        expected_plate_orientation: 0
      }
    }

    // Add overhang for Titan-native devices
    if (template.device_class === 'titan_native' && template.default_overhang) {
      device.overhang = {
        width: template.default_overhang.width,
        depth: template.default_overhang.depth,
        offset_x: (template.default_footprint.width - template.default_overhang.width) / 2,
        offset_y: template.default_footprint.height
      }
      // Nest is in the overhang area for native devices
      device.nest.x = template.default_footprint.width / 2
      device.nest.y = template.default_footprint.height + template.default_overhang.depth / 2
    }

    devices.value.push(device)
    selectedDeviceId.value = device.device_id

    return device
  }

  // Update device
  function updateDevice(deviceId: string, updates: Partial<Device>) {
    const index = devices.value.findIndex(d => d.device_id === deviceId)
    if (index === -1) return

    saveState()
    devices.value[index] = { ...devices.value[index], ...updates }
  }

  // Delete device
  function deleteDevice(deviceId: string) {
    const index = devices.value.findIndex(d => d.device_id === deviceId)
    if (index === -1) return

    saveState()
    devices.value.splice(index, 1)

    if (selectedDeviceId.value === deviceId) {
      selectedDeviceId.value = null
    }
  }

  // Select device
  function selectDevice(deviceId: string | null) {
    selectedDeviceId.value = deviceId
  }

  // Rotate device (by 90 degrees)
  function rotateDevice(deviceId: string, clockwise: boolean = true) {
    const device = devices.value.find(d => d.device_id === deviceId)
    if (!device) return

    saveState()

    const rotations: Orientation[] = [0, 90, 180, 270]
    const currentIndex = rotations.indexOf(device.orientation)
    const newIndex = clockwise
      ? (currentIndex + 1) % 4
      : (currentIndex + 3) % 4
    device.orientation = rotations[newIndex]
  }

  // Set device orientation to specific angle
  function setDeviceOrientation(deviceId: string, angle: number) {
    const device = devices.value.find(d => d.device_id === deviceId)
    if (!device) return

    // Normalize angle to 0, 90, 180, 270
    const validAngles: Orientation[] = [0, 90, 180, 270]
    const normalizedAngle = ((angle % 360) + 360) % 360
    const closestAngle = validAngles.reduce((prev, curr) =>
      Math.abs(curr - normalizedAngle) < Math.abs(prev - normalizedAngle) ? curr : prev
    )

    if (device.orientation !== closestAngle) {
      saveState()
      device.orientation = closestAngle
    }
  }

  // Move device
  function moveDevice(deviceId: string, position: { x: number; y: number }) {
    const device = devices.value.find(d => d.device_id === deviceId)
    if (!device) return

    device.position = { ...position }
  }

  // Move device with undo (call after drag ends)
  function moveDeviceWithUndo(deviceId: string, position: { x: number; y: number }) {
    saveState()
    moveDevice(deviceId, position)
  }

  // Snap position to grid (for Titan-native devices)
  function snapToTileEdge(
    position: { x: number; y: number },
    footprintWidth: number,
    footprintHeight: number,
    tileRow: number,
    tileCol: number,
    edge: 'top' | 'bottom' | 'left' | 'right'
  ): { x: number; y: number } {
    const tileX = tileCol * TILE_SIZE_MM
    const tileY = tileRow * TILE_SIZE_MM

    switch (edge) {
      case 'top':
        return {
          x: tileX + (TILE_SIZE_MM - footprintWidth) / 2,
          y: tileY - footprintHeight
        }
      case 'bottom':
        return {
          x: tileX + (TILE_SIZE_MM - footprintWidth) / 2,
          y: tileY + TILE_SIZE_MM
        }
      case 'left':
        return {
          x: tileX - footprintWidth,
          y: tileY + (TILE_SIZE_MM - footprintHeight) / 2
        }
      case 'right':
        return {
          x: tileX + TILE_SIZE_MM,
          y: tileY + (TILE_SIZE_MM - footprintHeight) / 2
        }
    }
  }

  // Canvas transform
  function setZoom(newZoom: number) {
    zoom.value = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom))
  }

  function zoomIn() {
    setZoom(zoom.value * 1.2)
  }

  function zoomOut() {
    setZoom(zoom.value / 1.2)
  }

  function zoomToFit(contentBounds: { minX: number; minY: number; maxX: number; maxY: number }, viewportSize: { width: number; height: number }) {
    const contentWidth = contentBounds.maxX - contentBounds.minX
    const contentHeight = contentBounds.maxY - contentBounds.minY

    if (contentWidth <= 0 || contentHeight <= 0) return

    const padding = 50
    const zoomX = (viewportSize.width - padding * 2) / contentWidth
    const zoomY = (viewportSize.height - padding * 2) / contentHeight
    const newZoom = Math.min(zoomX, zoomY, MAX_ZOOM)

    setZoom(Math.max(newZoom, MIN_ZOOM))

    // Center content
    panX.value = (viewportSize.width - contentWidth * zoom.value) / 2 - contentBounds.minX * zoom.value
    panY.value = (viewportSize.height - contentHeight * zoom.value) / 2 - contentBounds.minY * zoom.value
  }

  function resetView() {
    zoom.value = 1.0
    panX.value = 50
    panY.value = 50
  }

  // Layer visibility toggles
  function toggleLayer(layer: keyof LayerVisibility) {
    layers.value[layer] = !layers.value[layer]
  }

  function setLayerVisibility(layer: keyof LayerVisibility, visible: boolean) {
    layers.value[layer] = visible
  }

  // API operations
  async function loadDevices() {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<Device[]>(`${baseUrl}/api/config/devices`)
      devices.value = response
      undoStack.value = []
      redoStack.value = []
      isDirty.value = false
    } catch (e: unknown) {
      error.value = `Failed to load devices: ${e}`
      console.error('Failed to load devices:', e)
    } finally {
      loading.value = false
    }
  }

  async function saveDevices() {
    // Cancel pending auto-save
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }

    loading.value = true
    error.value = null
    try {
      await $fetch(`${baseUrl}/api/config/devices`, {
        method: 'PUT',
        body: devices.value
      })
      isDirty.value = false
    } catch (e: unknown) {
      error.value = `Failed to save devices: ${e}`
      console.error('Failed to save devices:', e)
    } finally {
      loading.value = false
    }
  }

  // Save immediately before navigation (returns promise for async navigation guards)
  async function saveBeforeNavigation(): Promise<void> {
    if (isDirty.value) {
      // Cancel pending auto-save
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer)
        autoSaveTimer = null
      }
      await saveDevicesInternal()
    }
  }

  // Cleanup function for component unmount
  function cleanup() {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
  }

  async function fetchDeviceHubDevices(): Promise<DeviceHubDevice[]> {
    try {
      const response = await $fetch<DeviceHubDevice[]>(`${baseUrl}/api/device_hub/devices`)
      return response
    } catch (e: unknown) {
      console.error('Failed to fetch DeviceHub devices:', e)
      return []
    }
  }

  // Get device color by type
  function getDeviceColor(deviceType: DeviceType): string {
    return DEVICE_COLORS[deviceType] || '#6b7280'
  }

  // Calculate device bounds (for selection, rotation handle, etc.)
  function getDeviceBounds(device: Device): { x: number; y: number; width: number; height: number } {
    // Account for rotation - swap width/height for 90° and 270°
    const isRotated = device.orientation === 90 || device.orientation === 270
    const width = isRotated ? device.footprint.height : device.footprint.width
    const height = isRotated ? device.footprint.width : device.footprint.height

    // Include overhang in bounds if present
    let totalHeight = height
    if (device.overhang) {
      totalHeight += device.overhang.depth
    }

    return {
      x: device.position.x,
      y: device.position.y,
      width,
      height: totalHeight
    }
  }

  return {
    // State
    devices,
    selectedDeviceId,
    selectedDevice,
    zoom,
    panX,
    panY,
    layers,
    isDragging,
    dragOffset,
    loading,
    error,
    isDirty,

    // Undo/redo
    canUndo,
    canRedo,
    undo,
    redo,

    // Device operations
    addDevice,
    updateDevice,
    deleteDevice,
    selectDevice,
    rotateDevice,
    setDeviceOrientation,
    moveDevice,
    moveDeviceWithUndo,
    snapToTileEdge,

    // Canvas operations
    setZoom,
    zoomIn,
    zoomOut,
    zoomToFit,
    resetView,

    // Layer operations
    toggleLayer,
    setLayerVisibility,

    // API operations
    loadDevices,
    saveDevices,
    saveBeforeNavigation,
    fetchDeviceHubDevices,
    cleanup,

    // Helpers
    getDeviceColor,
    getDeviceBounds
  }
}
