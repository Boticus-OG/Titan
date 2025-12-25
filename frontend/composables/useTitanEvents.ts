/**
 * Composable for Titan WebSocket events.
 *
 * Provides real-time event subscription for actor state changes.
 * Per Constitution Section 4.3: Event-Driven State Propagation.
 */

import type { ActorEvent } from '~/types/deck'

export function useTitanEvents() {
  const config = useRuntimeConfig()
  const wsUrl = `${config.public.wsBase || 'ws://localhost:8000'}/ws/events`

  const connected = ref(false)
  const events = ref<ActorEvent[]>([])
  const maxEvents = 100 // Keep last N events

  let ws: WebSocket | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

  /**
   * Event handlers by pattern.
   * Pattern supports wildcards: 'plate.*', 'mover.*', '**'
   */
  const handlers = new Map<string, Set<(event: ActorEvent) => void>>()

  /**
   * Connect to the WebSocket.
   */
  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        connected.value = true
        console.log('[Titan] WebSocket connected')
      }

      ws.onclose = () => {
        connected.value = false
        console.log('[Titan] WebSocket disconnected')
        scheduleReconnect()
      }

      ws.onerror = (error) => {
        console.error('[Titan] WebSocket error:', error)
      }

      ws.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as ActorEvent
          handleEvent(event)
        }
        catch (e) {
          console.warn('[Titan] Failed to parse event:', e)
        }
      }
    }
    catch (e) {
      console.error('[Titan] Failed to connect:', e)
      scheduleReconnect()
    }
  }

  /**
   * Disconnect from the WebSocket.
   */
  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  /**
   * Schedule a reconnection attempt.
   */
  function scheduleReconnect() {
    if (reconnectTimeout) return
    reconnectTimeout = setTimeout(() => {
      reconnectTimeout = null
      connect()
    }, 2000)
  }

  /**
   * Handle an incoming event.
   */
  function handleEvent(event: ActorEvent) {
    // Add to events list
    events.value.unshift(event)
    if (events.value.length > maxEvents) {
      events.value.pop()
    }

    // Dispatch to handlers
    handlers.forEach((callbacks, pattern) => {
      if (matchesPattern(event.event_type, pattern)) {
        callbacks.forEach((cb) => cb(event))
      }
    })
  }

  /**
   * Check if an event type matches a pattern.
   * Supports: 'plate.*', 'mover.transport_*', '**'
   */
  function matchesPattern(eventType: string, pattern: string): boolean {
    if (pattern === '**') return true

    const regex = pattern
      .replace(/\./g, '\\.')
      .replace(/\*\*/g, '.*')
      .replace(/\*/g, '[^.]*')

    return new RegExp(`^${regex}$`).test(eventType)
  }

  /**
   * Subscribe to events matching a pattern.
   */
  function on(pattern: string, callback: (event: ActorEvent) => void) {
    if (!handlers.has(pattern)) {
      handlers.set(pattern, new Set())
    }
    handlers.get(pattern)!.add(callback)

    // Return unsubscribe function
    return () => {
      handlers.get(pattern)?.delete(callback)
    }
  }

  /**
   * Send a message to the server.
   */
  function send(message: Record<string, unknown>) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    }
  }

  /**
   * Request actor state.
   */
  function requestState(actorId: string) {
    send({ type: 'get_state', actor_id: actorId })
  }

  // Auto-connect on client side
  if (import.meta.client) {
    onMounted(() => connect())
    onUnmounted(() => disconnect())
  }

  return {
    connected: readonly(connected),
    events: readonly(events),
    connect,
    disconnect,
    on,
    send,
    requestState,
  }
}
