/**
 * Device Configuration Types for System Configuration Tool
 *
 * Phase 1: Device Placement
 * - Titan-native devices: grid-aligned on 240x240mm tiles
 * - Third-party devices: free placement in surrounding space
 */

// Device type enumeration
export type DeviceType =
  | 'pipetter'
  | 'dispenser'
  | 'incubator'
  | 'reader'
  | 'washer'
  | 'centrifuge'
  | 'labeler'
  | 'sealer'
  | 'peeler'
  | 'lidmate'
  | 'decapper'
  | 'hotel'
  | 'barcode_reader'
  | 'robot'

// Device classification
export type DeviceClass = 'titan_native' | 'third_party'

// Cardinal rotation angles
export type Orientation = 0 | 90 | 180 | 270

// A1 corner position options
export type A1Position = 'upper_left' | 'upper_right' | 'lower_right' | 'lower_left'

/**
 * Configured device in the workcell
 */
export interface Device {
  device_id: string
  name: string
  device_type: DeviceType
  device_class: DeviceClass

  // Geometry
  footprint: {
    width: number   // mm
    height: number  // mm
  }

  // Position (absolute coordinates in mm)
  position: {
    x: number
    y: number
  }
  orientation: Orientation  // degrees clockwise

  // For Titan-native: associated tile grid position
  grid_pos?: {
    col: number
    row: number
  }

  // Nest (plate presentation point, relative to device origin)
  nest: {
    x: number       // mm relative to device origin
    y: number       // mm relative to device origin
    expected_plate_orientation: Orientation  // A1 corner position
  }

  // Overhang zone (end-effector area over deck)
  overhang?: {
    width: number     // mm (typically half of body width)
    depth: number     // mm (extends over tile)
    offset_x: number  // mm from device origin
    offset_y: number  // mm from device origin
  }

  // DeviceHub reference (optional)
  device_hub_id?: string
}

/**
 * Device template from palette
 */
export interface DeviceTemplate {
  device_type: DeviceType
  device_class: DeviceClass
  name: string
  icon?: string
  default_footprint: {
    width: number
    height: number
  }
  default_overhang?: {
    width: number
    depth: number
  }
}

/**
 * DeviceHub device info (from backend)
 */
export interface DeviceHubDevice {
  device_id: string
  device_type: string
  manufacturer: string
  model: string
  connection_status: 'connected' | 'disconnected' | 'error'
  available_commands: string[]
}

/**
 * Layer visibility configuration
 */
export interface LayerVisibility {
  tiles: boolean
  devices: boolean
  tracks: boolean
  teachPoints: boolean
  movers: boolean
  labels: boolean
}

/**
 * Workcell editor state
 */
export interface WorkcellEditorState {
  // Canvas transform
  zoom: number
  panX: number
  panY: number

  // Selection
  selectedDeviceId: string | null

  // Drag state
  isDragging: boolean
  dragOffset: { x: number; y: number } | null

  // Layer visibility
  layers: LayerVisibility

  // Undo/redo
  undoStack: Device[][]
  redoStack: Device[][]
}

/**
 * Device color palette by type
 */
export const DEVICE_COLORS: Record<DeviceType, string> = {
  pipetter: '#8b5cf6',     // Purple
  dispenser: '#06b6d4',    // Cyan
  incubator: '#f59e0b',    // Amber
  reader: '#10b981',       // Emerald
  washer: '#3b82f6',       // Blue
  lidmate: '#ec4899',      // Pink
  centrifuge: '#6366f1',   // Indigo
  hotel: '#64748b',        // Slate
  robot: '#ef4444',        // Red
  labeler: '#14b8a6',      // Teal
  sealer: '#f97316',       // Orange
  peeler: '#84cc16',       // Lime
  decapper: '#a855f7',     // Violet
  barcode_reader: '#22c55e' // Green
}

/**
 * Default device templates for palette
 *
 * Titan Native devices: 240x240mm body (matches tile size)
 * Overhang: 120mm wide (half body), 120mm depth (half tile)
 */
export const DEFAULT_DEVICE_TEMPLATES: DeviceTemplate[] = [
  // Titan Native devices - all 240x240mm body
  {
    device_type: 'pipetter',
    device_class: 'titan_native',
    name: 'Pipetter',
    default_footprint: { width: 240, height: 240 },
    default_overhang: { width: 120, depth: 120 }
  },
  {
    device_type: 'lidmate',
    device_class: 'titan_native',
    name: 'Lid Handler',
    default_footprint: { width: 240, height: 240 },
    default_overhang: { width: 120, depth: 120 }
  },
  {
    device_type: 'decapper',
    device_class: 'titan_native',
    name: 'Decapper',
    default_footprint: { width: 240, height: 240 },
    default_overhang: { width: 120, depth: 120 }
  },
  {
    device_type: 'dispenser',
    device_class: 'titan_native',
    name: 'Dispenser',
    default_footprint: { width: 240, height: 240 },
    default_overhang: { width: 120, depth: 120 }
  },
  // Third-party devices
  {
    device_type: 'incubator',
    device_class: 'third_party',
    name: 'Incubator',
    default_footprint: { width: 400, height: 350 }
  },
  {
    device_type: 'reader',
    device_class: 'third_party',
    name: 'Plate Reader',
    default_footprint: { width: 300, height: 250 }
  },
  {
    device_type: 'washer',
    device_class: 'third_party',
    name: 'Plate Washer',
    default_footprint: { width: 320, height: 280 }
  },
  {
    device_type: 'centrifuge',
    device_class: 'third_party',
    name: 'Centrifuge',
    default_footprint: { width: 350, height: 350 }
  },
  {
    device_type: 'hotel',
    device_class: 'third_party',
    name: 'Plate Hotel',
    default_footprint: { width: 200, height: 300 }
  },
  {
    device_type: 'robot',
    device_class: 'third_party',
    name: 'Robot Arm',
    default_footprint: { width: 250, height: 250 }
  }
]

/**
 * Constants
 */
export const TILE_SIZE_MM = 240
export const MOVER_WIDTH_MM = 140
export const MOVER_HEIGHT_MM = 118
export const DEFAULT_OVERHANG_DEPTH = 120  // Half tile
export const MIN_ZOOM = 0.25
export const MAX_ZOOM = 4.0
export const GRID_SNAP_SIZE = 5  // mm
