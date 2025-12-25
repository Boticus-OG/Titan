/**
 * Deck and actor types for Titan.
 *
 * Constitution Article VIII: Physical Layout
 * - Stator tiles: 240mm x 240mm
 * - Grid-aligned coordinate system
 * - Devices share same footprint
 */

export interface Position {
  x: number
  y: number
  c: number // rotation in degrees
}

export interface GridPosition {
  col: number
  row: number
}

export interface StatorTile {
  grid_pos: GridPosition
  enabled: boolean
  position: Position
  bounds: [number, number, number, number] // x_min, y_min, x_max, y_max
}

export type DeviceType =
  | 'pipetter'
  | 'dispenser'
  | 'washer'
  | 'incubator'
  | 'reader'
  | 'lidmate'
  | 'decapper'
  | 'hotel'
  | 'nest'
  | 'barcode_reader'

export interface Station {
  station_id: string
  name: string
  grid_pos: GridPosition
  position: Position
  device_type: DeviceType
  device_id: string | null
  slots: number
  occupied_slots: number
  is_available: boolean
  queue_grid_pos: GridPosition | null
}

export interface DeckConfig {
  name: string
  cols: number
  rows: number
  tile_size_mm: number
  width_mm: number
  height_mm: number
  tiles: StatorTile[]
  stations: Station[]
}

// Actor state types

export interface MoverPhysical {
  position: Position
  track_id: string | null
  track_position: number
  velocity: number
  state: 'idle' | 'assigned' | 'transporting'
}

export interface MoverState {
  actor_id: string
  mover_id: number
  available: boolean
  assigned_plate_id: string | null
  current_transport: string | null
  physical: MoverPhysical
}

export interface WorkflowState {
  workflow_id: string
  current_step: number
  total_steps: number
  progress_percent: number
}

export interface PlateState {
  actor_id: string
  plate_id: string
  phase: 'created' | 'ready' | 'requesting_mover' | 'awaiting_mover' | 'in_transit' | 'processing' | 'paused' | 'completed' | 'error' | 'aborted'
  workflow: WorkflowState | null
  current_station: string | null
  assigned_mover: string | null
  current_device: string | null
}

// Event types

export interface ActorEvent {
  event_type: string
  actor_id: string
  timestamp: string
  data: Record<string, unknown>
}
