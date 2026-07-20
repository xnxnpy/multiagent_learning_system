interface WebSocketOptions {
  maxReconnectAttempts?: number
  reconnectInterval?: number
  autoReconnect?: boolean
  heartbeatTime?: number
}

interface WebSocketListeners {
  open: Array<(event: Event) => void>
  close: Array<(event: CloseEvent) => void>
  error: Array<(error: Event) => void>
  message: Array<(data: any) => void>
}

class WebSocketClient {
  private url: string
  private options: Required<WebSocketOptions>
  private ws: WebSocket | null = null
  private reconnectAttempts: number = 0
  private listeners: WebSocketListeners = {
    open: [],
    close: [],
    error: [],
    message: []
  }
  private heartbeatInterval: number | null = null

  constructor(url: string, options: WebSocketOptions = {}) {
    this.url = url
    this.options = {
      maxReconnectAttempts: options.maxReconnectAttempts ?? 5,
      reconnectInterval: options.reconnectInterval ?? 3000,
      autoReconnect: options.autoReconnect !== false,
      heartbeatTime: options.heartbeatTime ?? 30000
    }
  }

  connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = this.url.includes('?')
        ? `${this.url}&token=${token}`
        : `${this.url}?token=${token}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = (event: Event) => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.listeners.open.forEach(callback => callback(event))
        resolve()
      }

      this.ws.onclose = (event: CloseEvent) => {
        console.log('WebSocket closed', event.code, event.reason)
        this.stopHeartbeat()
        this.listeners.close.forEach(callback => callback(event))

        if (this.options.autoReconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Reconnecting... (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`)
          setTimeout(() => {
            this.connect(token)
          }, this.options.reconnectInterval)
        }
      }

      this.ws.onerror = (error: Event) => {
        console.error('WebSocket error:', error)
        this.listeners.error.forEach(callback => callback(error))
      }

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          // 自动回复服务端 ping，保持心跳
          if (data.type === 'ping') {
            this.ws?.send(JSON.stringify({ type: 'pong' }))
            return
          }
          this.listeners.message.forEach(callback => callback(data))
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
    })
  }

  send(data: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  on(event: keyof WebSocketListeners, callback: Function): this {
    if (this.listeners[event]) {
      this.listeners[event].push(callback as any)
    }
    return this
  }

  off(event: keyof WebSocketListeners, callback: Function): this {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
    }
    return this
  }

  close(): void {
    this.options.autoReconnect = false
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close()
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      this.send({ type: 'ping' })
    }, this.options.heartbeatTime)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }
}

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

export const createTutorWebSocket = (token: string) => {
  return new WebSocketClient(`${WS_BASE_URL}/api/v1/tutor/ws/chat`, {
    autoReconnect: true,
    maxReconnectAttempts: 10,
    reconnectInterval: 3000,
    heartbeatTime: 30000
  })
}

export const createNotificationWebSocket = (token: string) => {
  // 注意：token 不在这里添加，而是在 connect(token) 方法中添加
  return new WebSocketClient(`${WS_BASE_URL}/api/v1/notifications/ws`, {
    autoReconnect: true,
    maxReconnectAttempts: 10,
    reconnectInterval: 3000,
    heartbeatTime: 30000
  })
}

export const createProfileChatWebSocket = (token: string) => {
  return new WebSocketClient(`${WS_BASE_URL}/api/v1/profile-chat/ws/chat`, {
    autoReconnect: true,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
    heartbeatTime: 30000
  })
}

export const createWorkflowWebSocket = (token: string) => {
  return new WebSocketClient(`${WS_BASE_URL}/api/v1/student/ws/workflow`, {
    autoReconnect: false,
    heartbeatTime: 30000
  })
}

export default WebSocketClient
