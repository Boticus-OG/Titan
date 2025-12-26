/**
 * Deck Editor API Composable
 *
 * API wrapper for deck configuration operations:
 * - Location CRUD
 * - Track CRUD
 * - Tile toggle
 * - Configuration export/import
 */

import type { DeckConfig, Location, LocationType, Track } from '~/types/deck'

export function useDeckEditor(options: {
  apiBase?: string
} = {}) {
  const { apiBase = 'http://localhost:8000' } = options

  // State
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Helper for API calls
  async function apiCall<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    loading.value = true
    error.value = null

    try {
      const options: RequestInit = {
        method,
        headers: { 'Content-Type': 'application/json' },
      }
      if (body) {
        options.body = JSON.stringify(body)
      }

      const response = await fetch(`${apiBase}${path}`, options)

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`HTTP ${response.status}: ${text}`)
      }

      return await response.json()
    } catch (e) {
      error.value = String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  // =========================================================================
  // Deck
  // =========================================================================

  async function getDeck(): Promise<DeckConfig> {
    return apiCall<DeckConfig>('GET', '/api/deck')
  }

  async function getLayout(): Promise<DeckConfig> {
    return apiCall<DeckConfig>('GET', '/api/deck/editor/layout')
  }

  // =========================================================================
  // Locations
  // =========================================================================

  async function getLocations(filter?: {
    type?: LocationType
    stationId?: string
  }): Promise<Location[]> {
    const params = new URLSearchParams()
    if (filter?.type) params.set('location_type', filter.type)
    if (filter?.stationId) params.set('station_id', filter.stationId)
    const query = params.toString() ? `?${params}` : ''
    return apiCall<Location[]>('GET', `/api/deck/locations${query}`)
  }

  async function getLocation(locationId: string): Promise<Location> {
    return apiCall<Location>('GET', `/api/deck/locations/${locationId}`)
  }

  async function createLocation(data: {
    name: string
    location_type: LocationType
    x: number
    y: number
    c?: number
    track_id?: number
    track_distance?: number
    station_id?: string
    metadata?: Record<string, unknown>
  }): Promise<Location> {
    return apiCall<Location>('POST', '/api/deck/locations', data)
  }

  async function updateLocation(
    locationId: string,
    data: {
      name?: string
      x?: number
      y?: number
      c?: number
      track_id?: number
      track_distance?: number
      station_id?: string
      metadata?: Record<string, unknown>
    }
  ): Promise<Location> {
    return apiCall<Location>('PUT', `/api/deck/locations/${locationId}`, data)
  }

  async function deleteLocation(locationId: string): Promise<void> {
    await apiCall<{ status: string }>('DELETE', `/api/deck/locations/${locationId}`)
  }

  async function teachLocation(locationId: string, moverId: string): Promise<Location> {
    return apiCall<Location>('POST', `/api/deck/locations/${locationId}/teach?mover_id=${moverId}`)
  }

  // =========================================================================
  // Tracks
  // =========================================================================

  async function getTracks(): Promise<Track[]> {
    return apiCall<Track[]>('GET', '/api/deck/tracks')
  }

  async function getTrack(trackId: number): Promise<Track> {
    return apiCall<Track>('GET', `/api/deck/tracks/${trackId}`)
  }

  async function createTrack(data: {
    name: string
    start_x: number
    start_y: number
    end_x: number
    end_y: number
    track_id?: number
  }): Promise<Track> {
    return apiCall<Track>('POST', '/api/deck/tracks', data)
  }

  async function updateTrack(
    trackId: number,
    data: {
      name?: string
      start_x?: number
      start_y?: number
      end_x?: number
      end_y?: number
    }
  ): Promise<Track> {
    return apiCall<Track>('PUT', `/api/deck/tracks/${trackId}`, data)
  }

  async function deleteTrack(trackId: number): Promise<void> {
    await apiCall<{ status: string }>('DELETE', `/api/deck/tracks/${trackId}`)
  }

  async function getQueuePointsOnTrack(trackId: number): Promise<Location[]> {
    return apiCall<Location[]>('GET', `/api/deck/tracks/${trackId}/queue-points`)
  }

  async function getTrackConnections(trackId: number): Promise<{ track_id: number; connected_tracks: number[] }> {
    return apiCall('GET', `/api/deck/tracks/${trackId}/connections`)
  }

  // =========================================================================
  // Editor Operations
  // =========================================================================

  async function toggleTile(col: number, row: number, enabled: boolean): Promise<void> {
    await apiCall<{ status: string }>('POST', '/api/deck/editor/tiles/toggle', { col, row, enabled })
  }

  async function resizeGrid(cols: number, rows: number): Promise<void> {
    await apiCall<{ status: string }>('POST', '/api/deck/editor/resize', { cols, rows })
  }

  async function getQuadrantPoints(): Promise<Array<{
    tile_col: number
    tile_row: number
    quadrant_x: number
    quadrant_y: number
    absolute_x: number
    absolute_y: number
  }>> {
    return apiCall('GET', '/api/deck/editor/quadrant-points')
  }

  async function exportConfiguration(): Promise<{
    version: string
    deck: unknown
    stations: unknown[]
    tracks: unknown[]
    locations: unknown[]
  }> {
    return apiCall('POST', '/api/deck/editor/export')
  }

  async function importConfiguration(file: File): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${apiBase}/api/deck/editor/import`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`HTTP ${response.status}: ${text}`)
      }
    } catch (e) {
      error.value = String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    loading: readonly(loading),
    error: readonly(error),

    // Deck
    getDeck,
    getLayout,

    // Locations
    getLocations,
    getLocation,
    createLocation,
    updateLocation,
    deleteLocation,
    teachLocation,

    // Tracks
    getTracks,
    getTrack,
    createTrack,
    updateTrack,
    deleteTrack,
    getQueuePointsOnTrack,
    getTrackConnections,

    // Editor
    toggleTile,
    resizeGrid,
    getQuadrantPoints,
    exportConfiguration,
    importConfiguration,
  }
}
