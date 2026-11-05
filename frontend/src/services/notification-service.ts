import { apiClient } from "./api"
import type {
  InAppNotification,
  NotificationPagination,
  NotificationUnreadCount,
} from "../types"

export interface ListNotificationsParams {
  workspaceId?: string
  isRead?: boolean
  includeArchived?: boolean
  actionType?: string
  cursor?: string
  limit?: number
}

export class NotificationService {
  public static async listNotifications(
    params: ListNotificationsParams = {}
  ): Promise<NotificationPagination> {
    const query = new URLSearchParams()
    if (params.workspaceId) query.set("workspace_id", params.workspaceId)
    if (params.isRead !== undefined) query.set("is_read", String(params.isRead))
    if (params.includeArchived) query.set("include_archived", "true")
    if (params.actionType) query.set("action_type", params.actionType)
    if (params.cursor) query.set("cursor", params.cursor)
    if (params.limit) query.set("limit", String(params.limit))

    const qs = query.toString()
    const path = `/notifications${qs ? `?${qs}` : ""}`
    const res = await apiClient.get<NotificationPagination>(path)
    return res.data
  }

  public static async getUnreadCount(workspaceId?: string): Promise<number> {
    const query = new URLSearchParams()
    if (workspaceId) query.set("workspace_id", workspaceId)
    const qs = query.toString()
    const path = `/notifications/unread-count${qs ? `?${qs}` : ""}`
    const res = await apiClient.get<NotificationUnreadCount>(path)
    return res.data?.unread_count ?? 0
  }

  public static async markAsRead(notificationId: string): Promise<InAppNotification> {
    const res = await apiClient.patch<InAppNotification>(
      `/notifications/${notificationId}/read`
    )
    return res.data
  }

  public static async markAsUnread(notificationId: string): Promise<InAppNotification> {
    const res = await apiClient.patch<InAppNotification>(
      `/notifications/${notificationId}/unread`
    )
    return res.data
  }

  public static async markAllAsRead(workspaceId?: string): Promise<number> {
    const res = await apiClient.post<{ updated_count: number }>(
      "/notifications/read-all",
      { workspace_id: workspaceId || null }
    )
    return res.data?.updated_count ?? 0
  }

  public static async archiveNotification(
    notificationId: string
  ): Promise<InAppNotification> {
    const res = await apiClient.post<InAppNotification>(
      `/notifications/${notificationId}/archive`
    )
    return res.data
  }
}

