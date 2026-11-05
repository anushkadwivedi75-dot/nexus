import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Bell, CheckCheck, Inbox } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { useNotificationStore } from "@/stores/notification-store"
import { NotificationItem } from "./notification-item"

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const {
    notifications,
    unreadCount,
    fetchUnreadCount,
    fetchNotifications,
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

  const previewNotifications = notifications.slice(0, 5)

  const handleNotificationClick = (notif: (typeof notifications)[0]) => {
    if (!notif.is_read) {
      markAsRead(notif.id)
    }
    setOpen(false)
    if (notif.payload?.task_id) {
      navigate("/tasks")
    } else {
      navigate("/inbox")
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="relative text-muted-foreground hover:text-foreground"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground shadow-xs">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="w-80 sm:w-96 p-0 shadow-2xl border-border/80 bg-background/95 backdrop-blur-md rounded-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">Notifications</span>
            {unreadCount > 0 && (
              <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                {unreadCount} new
              </span>
            )}
          </div>

          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => markAllAsRead()}
              className="h-7 text-xs text-muted-foreground hover:text-foreground px-2"
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1 text-primary" />
              Mark all read
            </Button>
          )}
        </div>

        {/* Notification list */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1.5 divide-y divide-border/20">
          {previewNotifications.length > 0 ? (
            previewNotifications.map((notif) => (
              <NotificationItem
                key={notif.id}
                notification={notif}
                compact
                onMarkRead={markAsRead}
                onMarkUnread={markAsUnread}
                onArchive={archiveNotification}
                onClick={() => handleNotificationClick(notif)}
              />
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted/50 text-muted-foreground mb-2">
                <Inbox className="h-5 w-5" />
              </div>
              <p className="text-xs font-medium text-foreground">All caught up</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                No new notifications to show
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border/60 p-2 text-center bg-card/30">
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs text-muted-foreground hover:text-foreground h-8"
            onClick={() => {
              setOpen(false)
              navigate("/inbox")
            }}
          >
            View all in Inbox
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
