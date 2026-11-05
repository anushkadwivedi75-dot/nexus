import { create } from "zustand"
import { NotificationService } from "../services/notification-service"
import { realTimeClient, type EventEnvelope } from "../services/websocket-client"
import type { InAppNotification } from "../types"

export type NotificationTab = "all" | "unread" | "mentions" | "assignments" | "archived"

interface NotificationState {
  notifications: InAppNotification[]
  unreadCount: number
  isLoading: boolean
  hasMore: boolean
  nextCursor: string | null
  activeTab: NotificationTab
  error: string | null
  isRealtimeInitialized: boolean

  setActiveTab: (tab: NotificationTab) => void
  fetchUnreadCount: (workspaceId?: string) => Promise<void>
  fetchNotifications: (options?: { reset?: boolean; cursor?: string }) => Promise<void>
  markAsRead: (id: string) => Promise<void>
  markAsUnread: (id: string) => Promise<void>
  markAllAsRead: (workspaceId?: string) => Promise<void>
  archiveNotification: (id: string) => Promise<void>
  initRealtimeListener: () => () => void
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  hasMore: false,
  nextCursor: null,
  activeTab: "all",
  error: null,
  isRealtimeInitialized: false,

  setActiveTab: (tab: NotificationTab) => {
    set({ activeTab: tab })
    get().fetchNotifications({ reset: true })
  },

  fetchUnreadCount: async (workspaceId?: string) => {
    try {
      const count = await NotificationService.getUnreadCount(workspaceId)
      set({ unreadCount: count })
    } catch {
      // Keep optimistic count
    }
  },

  fetchNotifications: async (options = {}) => {
    const { reset = false, cursor } = options
    const { activeTab, notifications, nextCursor, isLoading } = get()
    if (isLoading) return

    set({ isLoading: true, error: null })

    try {
      let isRead: boolean | undefined = undefined
      let includeArchived = false
      let actionType: string | undefined = undefined

      if (activeTab === "unread") {
        isRead = false
      } else if (activeTab === "mentions") {
        actionType = "comment_mention"
      } else if (activeTab === "assignments") {
        actionType = "task_assigned"
      } else if (activeTab === "archived") {
        includeArchived = true
      }

      const targetCursor = reset ? undefined : cursor || nextCursor || undefined
      const data = await NotificationService.listNotifications({
        isRead,
        includeArchived,
        actionType,
        cursor: targetCursor,
        limit: 20,
      })

      const combined = reset ? data.items : [...notifications, ...data.items]
      set({
        notifications: combined,
        hasMore: data.has_more,
        nextCursor: data.next_cursor || null,
        unreadCount: data.unread_count,
        isLoading: false,
      })
    } catch (err: any) {
      set({
        error: err.message || "Failed to load notifications",
        isLoading: false,
      })
    }
  },

  markAsRead: async (id: string) => {
    const { notifications, unreadCount } = get()
    // Optimistic update
    set({
      notifications: notifications.map((n) =>
        n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
      ),
      unreadCount: Math.max(0, unreadCount - 1),
    })

    try {
      await NotificationService.markAsRead(id)
    } catch {
      // Revert if failed
      set({ notifications, unreadCount })
    }
  },

  markAsUnread: async (id: string) => {
    const { notifications, unreadCount } = get()
    // Optimistic update
    set({
      notifications: notifications.map((n) =>
        n.id === id ? { ...n, is_read: false, read_at: null } : n
      ),
      unreadCount: unreadCount + 1,
    })

    try {
      await NotificationService.markAsUnread(id)
    } catch {
      set({ notifications, unreadCount })
    }
  },

  markAllAsRead: async (workspaceId?: string) => {
    const { notifications } = get()
    set({
      notifications: notifications.map((n) => ({
        ...n,
        is_read: true,
        read_at: new Date().toISOString(),
      })),
      unreadCount: 0,
    })

    try {
      await NotificationService.markAllAsRead(workspaceId)
    } catch {
      get().fetchNotifications({ reset: true })
    }
  },

  archiveNotification: async (id: string) => {
    const { notifications, activeTab, unreadCount } = get()
    const target = notifications.find((n) => n.id === id)
    const wasUnread = target && !target.is_read

    // Optimistic update: remove from active view unless on archived tab
    set({
      notifications:
        activeTab === "archived"
          ? notifications.map((n) =>
              n.id === id ? { ...n, archived_at: new Date().toISOString() } : n
            )
          : notifications.filter((n) => n.id !== id),
      unreadCount: wasUnread ? Math.max(0, unreadCount - 1) : unreadCount,
    })

    try {
      await NotificationService.archiveNotification(id)
    } catch {
      set({ notifications, unreadCount })
    }
  },

  initRealtimeListener: () => {
    if (get().isRealtimeInitialized) {
      return () => {}
    }

    set({ isRealtimeInitialized: true })

    const unsubscribe = realTimeClient.onEvent((event: EventEnvelope) => {
      if (!event.event_type.startsWith("notification.")) return

      const { event_type, payload } = event
      const state = get()

      if (event_type === "notification.created") {
        const newNotif: InAppNotification = {
          id: payload.notification_id || event.entity_id,
          workspace_id: payload.workspace_id || event.workspace_id,
          recipient_id: payload.recipient_id,
          actor_id: payload.actor_id || event.actor_id,
          actor: payload.actor || null,
          action_type: payload.action_type,
          entity_type: payload.entity_type,
          entity_id: payload.entity_id,
          message: payload.message,
          payload: payload.payload || {},
          is_read: false,
          read_at: null,
          archived_at: null,
          created_at: payload.created_at || event.occurred_at,
        }

        // Prepend notification if not already in state
        if (!state.notifications.some((n) => n.id === newNotif.id)) {
          set({
            notifications: [newNotif, ...state.notifications],
            unreadCount: state.unreadCount + 1,
          })
        }
      } else if (event_type === "notification.read") {
        const notifId = payload.notification_id || event.entity_id
        set({
          notifications: state.notifications.map((n) =>
            n.id === notifId ? { ...n, is_read: true, read_at: payload.read_at } : n
          ),
          unreadCount: Math.max(0, state.unreadCount - 1),
        })
      } else if (event_type === "notification.unread") {
        const notifId = payload.notification_id || event.entity_id
        set({
          notifications: state.notifications.map((n) =>
            n.id === notifId ? { ...n, is_read: false, read_at: null } : n
          ),
          unreadCount: state.unreadCount + 1,
        })
      } else if (event_type === "notification.read_all") {
        set({
          notifications: state.notifications.map((n) => ({
            ...n,
            is_read: true,
            read_at: payload.read_at || new Date().toISOString(),
          })),
          unreadCount: 0,
        })
      } else if (event_type === "notification.archived") {
        const notifId = payload.notification_id || event.entity_id
        if (state.activeTab !== "archived") {
          set({
            notifications: state.notifications.filter((n) => n.id !== notifId),
          })
        }
      }
    })

    return () => {
      unsubscribe()
      set({ isRealtimeInitialized: false })
    }
  },
}))

