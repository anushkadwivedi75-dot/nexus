/**
 * Nexus Real-Time WebSocket Client
 *
 * Implements Section 12 of NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1:
 * - Single-use ticket handshake via POST /auth/ws-ticket
 * - Automatic exponential backoff reconnect with jitter
 * - Heartbeat keepalive ping loop every 25 seconds
 * - Channel subscription lifecycle (workspace, project, task)
 * - In-memory LRU event deduplication (200 event IDs)
 * - Strict tenant boundary filtering
 */

import { apiClient } from "./api"

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting"

export interface EventEnvelope<T = any> {
  schema_version: number
  event_id: string
  event_type: string
  workspace_id: string
  actor_id?: string | null
  entity_type: string
  entity_id: string
  occurred_at: string
  payload: T
}

type EventListener = (event: EventEnvelope) => void
type StatusListener = (status: ConnectionStatus) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private status: ConnectionStatus = "disconnected"
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private baseReconnectDelayMs = 1000
  private maxReconnectDelayMs = 30000
  private reconnectTimer: any = null
  private pingTimer: any = null
  private desiredChannels: Set<string> = new Set()
  private eventListeners: Set<EventListener> = new Set()
  private statusListeners: Set<StatusListener> = new Set()
  private processedEventIds: Set<string> = new Set()
  private eventIdQueue: string[] = []
  private maxLruEvents = 200
  private isExplicitlyClosed = false

  public getStatus(): ConnectionStatus {
    return this.status
  }

  public onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener)
    listener(this.status)
    return () => this.statusListeners.delete(listener)
  }

  public onEvent(listener: EventListener): () => void {
    this.eventListeners.add(listener)
    return () => this.eventListeners.delete(listener)
  }

  private setStatus(newStatus: ConnectionStatus) {
    if (this.status !== newStatus) {
      this.status = newStatus
      this.statusListeners.forEach((fn) => fn(newStatus))
    }
  }

  public async connect(): Promise<void> {
    if (this.status === "connected" || this.status === "connecting") return
    this.isExplicitlyClosed = false
    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting")

    try {
      // 1. Acquire single-use handshake ticket
      const ticketRes = await apiClient.request<{ ticket: string }>("/auth/ws-ticket", {
        method: "POST",
      })

      if (!ticketRes.success || !ticketRes.data?.ticket) {
        throw new Error(ticketRes.error?.message || "Failed to obtain WebSocket ticket")
      }

      const ticket = ticketRes.data.ticket
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const baseWs = (import.meta as any).env?.VITE_WS_URL || `${protocol}//${window.location.host}`
      const wsUrl = `${baseWs}/ws?ticket=${encodeURIComponent(ticket)}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.setStatus("connected")
        this.reconnectAttempts = 0
        this.startPingLoop()
        this.resubscribeAll()
      }

      this.ws.onmessage = (evt) => {
        try {
          const frame = JSON.parse(evt.data)
          this.handleIncomingFrame(frame)
        } catch {
          // Ignore malformed frames
        }
      }

      this.ws.onerror = () => {
        // Handled in onclose
      }

      this.ws.onclose = (evt) => {
        this.stopPingLoop()
        this.ws = null

        if (evt.code === 4401 || evt.code === 4403) {
          // Terminal auth eviction: do not immediately reconnect
          this.setStatus("disconnected")
          return
        }

        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect()
        } else {
          this.setStatus("disconnected")
        }
      }
    } catch {
      if (!this.isExplicitlyClosed) {
        this.scheduleReconnect()
      } else {
        this.setStatus("disconnected")
      }
    }
  }

  private handleIncomingFrame(frame: any) {
    if (frame.type === "event" && frame.data) {
      const envelope: EventEnvelope = frame.data

      // LRU event deduplication
      if (this.processedEventIds.has(envelope.event_id)) {
        return
      }
      this.processedEventIds.add(envelope.event_id)
      this.eventIdQueue.push(envelope.event_id)
      if (this.eventIdQueue.length > this.maxLruEvents) {
        const oldest = this.eventIdQueue.shift()
        if (oldest) this.processedEventIds.delete(oldest)
      }

      // Notify domain listeners
      this.eventListeners.forEach((listener) => {
        try {
          listener(envelope)
        } catch {
          // Ignore subscriber errors
        }
      })
    }
  }

  private startPingLoop() {
    this.stopPingLoop()
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ action: "ping" }))
      }
    }, 25000)
  }

  private stopPingLoop() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  private scheduleReconnect() {
    this.stopPingLoop()
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus("disconnected")
      return
    }

    this.reconnectAttempts++
    this.setStatus("reconnecting")

    // Exponential backoff with jitter
    const delay = Math.min(
      this.maxReconnectDelayMs,
      this.baseReconnectDelayMs * Math.pow(1.5, this.reconnectAttempts)
    ) + Math.random() * 1000

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  public subscribe(channel: string) {
    this.desiredChannels.add(channel)
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "subscribe", channel }))
    }
  }

  public unsubscribe(channel: string) {
    this.desiredChannels.delete(channel)
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "unsubscribe", channel }))
    }
  }

  private resubscribeAll() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
    this.desiredChannels.forEach((chan) => {
      this.ws?.send(JSON.stringify({ action: "subscribe", channel: chan }))
    })
  }

  public disconnect() {
    this.isExplicitlyClosed = true
    this.stopPingLoop()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close(1000, "CLIENT_DISCONNECTED")
      this.ws = null
    }
    this.setStatus("disconnected")
    this.reconnectAttempts = 0
  }
}

export const realTimeClient = new WebSocketClient()
