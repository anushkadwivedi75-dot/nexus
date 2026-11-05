import {
  AtSign,
  MessageSquareReply,
  UserCheck,
  UserMinus,
  ArrowRightLeft,
  ShieldCheck,
  UserPlus,
  Bell,
  Check,
  Archive,
  RotateCcw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { formatRelativeTime } from "@/lib/utils"
import type { InAppNotification } from "@/types"

interface NotificationItemProps {
  notification: InAppNotification
  onMarkRead?: (id: string) => void
  onMarkUnread?: (id: string) => void
  onArchive?: (id: string) => void
  compact?: boolean
  onClick?: () => void
}

export function NotificationItem({
  notification,
  onMarkRead,
  onMarkUnread,
  onArchive,
  compact = false,
  onClick,
}: NotificationItemProps) {
  const getIcon = () => {
    switch (notification.action_type) {
      case "comment_mention":
        return <AtSign className="h-3.5 w-3.5 text-blue-400" />
      case "comment_reply":
        return <MessageSquareReply className="h-3.5 w-3.5 text-violet-400" />
      case "task_assigned":
        return <UserCheck className="h-3.5 w-3.5 text-emerald-400" />
      case "task_unassigned":
        return <UserMinus className="h-3.5 w-3.5 text-amber-400" />
      case "task_status_changed":
        return <ArrowRightLeft className="h-3.5 w-3.5 text-indigo-400" />
      case "workspace_ownership_transferred":
        return <ShieldCheck className="h-3.5 w-3.5 text-yellow-400" />
      case "workspace_invitation_accepted":
        return <UserPlus className="h-3.5 w-3.5 text-green-400" />
      default:
        return <Bell className="h-3.5 w-3.5 text-primary" />
    }
  }

  const getIconBg = () => {
    switch (notification.action_type) {
      case "comment_mention":
        return "bg-blue-500/10 border-blue-500/20"
      case "comment_reply":
        return "bg-violet-500/10 border-violet-500/20"
      case "task_assigned":
        return "bg-emerald-500/10 border-emerald-500/20"
      case "task_unassigned":
        return "bg-amber-500/10 border-amber-500/20"
      case "task_status_changed":
        return "bg-indigo-500/10 border-indigo-500/20"
      case "workspace_ownership_transferred":
        return "bg-yellow-500/10 border-yellow-500/20"
      case "workspace_invitation_accepted":
        return "bg-green-500/10 border-green-500/20"
      default:
        return "bg-primary/10 border-primary/20"
    }
  }

  return (
    <div
      onClick={onClick}
      className={`group relative flex items-start gap-3 rounded-lg border p-3 transition-all ${
        notification.is_read
          ? "border-border/40 bg-card/40 opacity-80 hover:opacity-100 hover:bg-card/70"
          : "border-border/80 bg-card/90 shadow-2xs hover:border-border hover:bg-card"
      } ${onClick ? "cursor-pointer" : ""}`}
    >
      {/* Icon */}
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border mt-0.5 ${getIconBg()}`}
      >
        {getIcon()}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pr-6">
        <p className="text-xs text-foreground leading-snug">
          {notification.message}
        </p>

        {notification.payload?.snippet && !compact && (
          <p className="mt-1 text-[11px] text-muted-foreground line-clamp-2 italic bg-muted/30 rounded px-2 py-1 border border-border/40">
            "{notification.payload.snippet}"
          </p>
        )}

        <div className="mt-1.5 flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground/80">
            {formatRelativeTime(notification.created_at)}
          </span>
          {notification.payload?.task_number && (
            <span className="rounded bg-muted/60 px-1.5 py-0.2 text-[9px] font-mono text-muted-foreground">
              {notification.payload.task_number}
            </span>
          )}
        </div>
      </div>

      {/* Unread indicator */}
      {!notification.is_read && (
        <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary" />
      )}

      {/* Actions (hover overlay) */}
      <div className="absolute top-2 right-2 hidden group-hover:flex items-center gap-1 bg-card/90 backdrop-blur-xs p-0.5 rounded-md border border-border/60 shadow-xs">
        {notification.is_read ? (
          onMarkUnread && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              title="Mark as unread"
              onClick={(e) => {
                e.stopPropagation()
                onMarkUnread(notification.id)
              }}
            >
              <RotateCcw className="h-3 w-3" />
            </Button>
          )
        ) : (
          onMarkRead && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              title="Mark as read"
              onClick={(e) => {
                e.stopPropagation()
                onMarkRead(notification.id)
              }}
            >
              <Check className="h-3 w-3" />
            </Button>
          )
        )}

        {onArchive && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="h-6 w-6 text-muted-foreground hover:text-foreground"
            title="Archive"
            onClick={(e) => {
              e.stopPropagation()
              onArchive(notification.id)
            }}
          >
            <Archive className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  )
}
