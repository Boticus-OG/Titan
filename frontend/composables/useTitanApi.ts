/**
 * Composable for Titan API access.
 *
 * Provides typed access to the Titan REST API endpoints.
 */

import type { DeckConfig, MoverState, PlateState, Station } from '~/types/deck'

export function useTitanApi() {
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBase || ''

  /**
   * Get the current deck configuration.
   */
  async function getDeck(): Promise<DeckConfig> {
    const response = await $fetch<DeckConfig>(`${baseUrl}/api/deck`)
    return response
  }

  /**
   * Get all stations on the deck.
   */
  async function getStations(): Promise<Station[]> {
    const response = await $fetch<Station[]>(`${baseUrl}/api/deck/stations`)
    return response
  }

  /**
   * Get system status.
   */
  async function getStatus() {
    return $fetch(`${baseUrl}/api/status`)
  }

  /**
   * Get all plates.
   */
  async function getPlates(): Promise<Record<string, PlateState>> {
    return $fetch(`${baseUrl}/api/plates`)
  }

  /**
   * Get a specific plate.
   */
  async function getPlate(plateId: string): Promise<PlateState> {
    return $fetch(`${baseUrl}/api/plates/${plateId}`)
  }

  /**
   * Create a new plate.
   */
  async function createPlate(plateId: string): Promise<{ status: string; plate_id: string }> {
    return $fetch(`${baseUrl}/api/plates`, {
      method: 'POST',
      query: { plate_id: plateId },
    })
  }

  /**
   * Get all movers.
   */
  async function getMovers(): Promise<Record<string, MoverState>> {
    return $fetch(`${baseUrl}/api/movers`)
  }

  /**
   * Get a specific mover.
   */
  async function getMover(moverId: string): Promise<MoverState> {
    return $fetch(`${baseUrl}/api/movers/${moverId}`)
  }

  /**
   * Run the demo workflow.
   */
  async function runDemo() {
    return $fetch(`${baseUrl}/api/demo/run`, { method: 'POST' })
  }

  return {
    getDeck,
    getStations,
    getStatus,
    getPlates,
    getPlate,
    createPlate,
    getMovers,
    getMover,
    runDemo,
  }
}
