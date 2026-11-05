import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
  CheckCheck,
  RefreshCw,
  Inbox,
  AtSign,
  UserCheck,
  Archive,
  Layers,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  useNotificationStore,
  type NotificationTab,
} from "@/stores/notification-store"
import { NotificationItem } from "@/components/notifications/notification-item"

export function InboxPage() {
  const navigate = useNavigate()
  const {
    notifications,
    unreadCount,
    isLoading,
    hasMore,
    activeTab,
    setActiveTab,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAsUnread,
    markAllAsRead,
    archiveNotification,
    initRealtimeListener,
  } = useNotificationStore()

  useEffect(() => {
    fetchUnreadCount()
    fetchNotifications({ reset: true })
    const cleanup = initRealtimeListener()
    return cleanup
  }, [fetchUnreadCount, fetchNotifications, initRealtimeListener])

  const tabs: { id: NotificationTab; label: string; icon: any; count?: number }[] = [
    { id: "all", label: "All", icon: Layers },
    { id: "unread", label: "Unread", icon: Inbox, count: unreadCount },
    { id: "mentions", label: "Mentions", icon: AtSign },
    { id: "assignments", label: "Assignments", icon: UserCheck },
    { id: "archived", label: "Archived", icon: Archive },
  ]

  const handleItemClick = (notif: (typeof notifications)[0]) => {
    if (!notif.is_read) {
      markAsRead(notif.id)
    }
    if (notif.payload?.task_id) {
      navigate("/tasks")
    }
  }

  const getEmptyMessage = () => {
    switch (activeTab) {
      case "unread":
        return {
          title: "Zero unread notifications",
          desc: "You've reviewed all incoming notifications. Great job!",
        }
      case "mentions":
        return {
          title: "No mentions yet",
          desc: "When teammates @mention you in comments, they will appear here.",
        }
      case "assignments":
        return {
          title: "No assignments",
          desc: "Tasks assigned to you will be tracked here.",
        }
      case "archived":
        return {
          title: "Archive is empty",
          desc: "Notifications you archive will be kept here for reference.",
        }
      default:
        return {
          title: "Inbox Zero",
          desc: "No notifications to show. You are completely up to date.",
        }
    }
  }

  const emptyInfo = getEmptyMessage()

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              Inbox
            </h1>
            {unreadCount > 0 && (
              <span className="rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-semibold text-primary">
                {unreadCount} unread
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time mentions, assignments, and workspace activity alerts
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={isLoading}
            onClick={() => {
              fetchUnreadCount()
              fetchNotifications({ reset: true })
            }}
            className="text-xs h-8 px-2.5"
            title="Refresh inbox"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          {unreadCount > 0 && (
            <Button
              variant="subtle"
              size="sm"
              onClick={() => markAllAsRead()}
              className="text-xs h-8 px-3"
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1.5 text-primary" />
              Mark all read
            </Button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 border-b border-border/40 pb-2 overflow-x-auto select-none">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? "bg-primary/15 text-primary shadow-2xs font-semibold"
                  : "text-muted-foreground hover:bg-card hover:text-foreground"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{tab.label}</span>
              {typeof tab.count === "number" && tab.count > 0 && (
                <span className="rounded-full bg-primary text-primary-foreground text-[10px] font-bold px-1.5 py-0.2">
                  {tab.count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Notifications List */}
      <div className="space-y-2">
        {notifications.length > 0 ? (
          notifications.map((notif) => (
            <NotificationItem
              key={notif.id}
              notification={notif}
              onMarkRead={markAsRead}
              onMarkUnread={markAsUnread}
              onArchive={archiveNotification}
              onClick={() => handleItemClick(notif)}
            />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center rounded-xl border border-border/50 bg-card/20 p-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/60 text-muted-foreground mb-3 shadow-inner">
              <Inbox className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">{emptyInfo.title}</h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm">
              {emptyInfo.desc}
            </p>
          </div>
        )}

        {/* Load More Pagination */}
        {hasMore && (
          <div className="flex justify-center pt-4">
            <Button
              variant="outline"
              size="sm"
              disabled={isLoading}
              onClick={() => fetchNotifications()}
              className="text-xs px-4"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="h-3 w-3 mr-1.5 animate-spin" />
                  Loading...
                </>
              ) : (
                "Load more notifications"
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
