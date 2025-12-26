/**
 * Mover Tracking Composable
 *
 * Provides real-time mover position tracking via WebSocket
 * with fallback to polling if WebSocket is unavailable.
 */

import type { MoverState, Position } from '~/types/deck'

interface MoverPositionEvent {
  type: 'mover_positions'
  positions: Record<string, Position>
  timestamp: string
}

export function useMoverTracking(options: {
  apiBase?: string
  wsBase?: string
  pollInterval?: number
} = {}) {
  const {
    apiBase = 'http://localhost:8000',
    wsBase = 'ws://localhost:8000',
    pollInterval = 500,
  } = options

  // State
  const positions = ref<Record<string, Position>>({})
  const movers = ref<MoverState[]>([])
  const connected = ref(false)
  const connectionType = ref<'websocket' | 'polling' | 'none'>('none')
  const error = ref<string | null>(null)

  // WebSocket connection
  let ws: WebSocket | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5

  // Position history for velocity calculation
  const positionHistory = new Map<string, Array<{ pos: Position; time: number }>>()
  const historyMaxLength = 10

  // Computed velocities
  const velocities = computed(() => {
    const result: Record<string, number> = {}
    for (const [moverId, history] of positionHistory.entries()) {
      if (history.length >= 2) {
        const latest = history[history.length - 1]
        const previous = history[history.length - 2]
        const dt = (latest.time - previous.time) / 1000 // seconds
        if (dt > 0) {
          const dx = latest.pos.x - previous.pos.x
          const dy = latest.pos.y - previous.pos.y
          const distance = Math.sqrt(dx * dx + dy * dy)
          result[moverId] = distance / dt // mm/s
        }
      }
    }
    return result
  })

  // Update position and history
  function updatePosition(moverId: string, pos: Position) {
    positions.value[moverId] = pos

    // Update history
    let history = positionHistory.get(moverId)
    if (!history) {
      history = []
      positionHistory.set(moverId, history)
    }
    history.push({ pos, time: Date.now() })
    if (history.length > historyMaxLength) {
      history.shift()
    }
  }

  // Connect via WebSocket
  function connectWebSocket() {
    if (ws) {
      ws.close()
    }

    try {
      ws = new WebSocket(`${wsBase}/ws/events`)

      ws.onopen = () => {
        connected.value = true
        connectionType.value = 'websocket'
        error.value = null
        reconnectAttempts = 0
        console.log('MoverTracking: WebSocket connected')

        // Stop polling if it was running
        if (pollTimer) {
          clearInterval(pollTimer)
          pollTimer = null
        }
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'mover_positions') {
            const posEvent = data as MoverPositionEvent
            for (const [moverId, pos] of Object.entries(posEvent.positions)) {
              updatePosition(moverId, pos)
            }
          }
        } catch (e) {
          console.error('MoverTracking: Failed to parse message', e)
        }
      }

      ws.onclose = () => {
        connected.value = false
        connectionType.value = 'none'
        console.log('MoverTracking: WebSocket disconnected')

        // Try to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
          console.log(`MoverTracking: Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)
          reconnectTimer = setTimeout(connectWebSocket, delay)
        } else {
          console.log('MoverTracking: Max reconnect attempts reached, falling back to polling')
          startPolling()
        }
      }

      ws.onerror = (e) => {
        console.error('MoverTracking: WebSocket error', e)
        error.value = 'WebSocket connection failed'
      }
    } catch (e) {
      console.error('MoverTracking: Failed to create WebSocket', e)
      startPolling()
    }
  }

  // Fetch movers via REST API
  async function fetchMovers() {
    try {
      const response = await fetch(`${apiBase}/api/movers`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()

      movers.value = Object.values(data) as MoverState[]

      // Update positions from mover state
      for (const mover of movers.value) {
        if (mover.physical?.position) {
          updatePosition(mover.actor_id, mover.physical.position)
        }
      }

      if (!connected.value) {
        connected.value = true
        connectionType.value = 'polling'
        error.value = null
      }
    } catch (e) {
      console.error('MoverTracking: Failed to fetch movers', e)
      error.value = `Failed to fetch movers: ${e}`
      connected.value = false
    }
  }

  // Start polling
  function startPolling() {
    if (pollTimer) return

    console.log('MoverTracking: Starting polling')
    connectionType.value = 'polling'
    pollTimer = setInterval(fetchMovers, pollInterval)
    fetchMovers() // Immediate first fetch
  }

  // Stop polling
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  // Connect (try WebSocket first, fall back to polling)
  function connect() {
    connectWebSocket()

    // Start polling as fallback after a delay
    setTimeout(() => {
      if (!connected.value) {
        console.log('MoverTracking: WebSocket not connected, starting polling')
        startPolling()
      }
    }, 2000)
  }

  // Disconnect
  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    stopPolling()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    connected.value = false
    connectionType.value = 'none'
  }

  // Get mover by ID
  function getMover(moverId: string): MoverState | undefined {
    return movers.value.find((m) => m.actor_id === moverId)
  }

  // Get position by mover ID
  function getPosition(moverId: string): Position | undefined {
    return positions.value[moverId]
  }

  // Get velocity by mover ID
  function getVelocity(moverId: string): number {
    return velocities.value[moverId] || 0
  }

  // Auto-connect on mount
  onMounted(() => {
    connect()
  })

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    positions: readonly(positions),
    movers: readonly(movers),
    velocities,
    connected: readonly(connected),
    connectionType: readonly(connectionType),
    error: readonly(error),

    // Methods
    connect,
    disconnect,
    getMover,
    getPosition,
    getVelocity,
    fetchMovers,
  }
}
