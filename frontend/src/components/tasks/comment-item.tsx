import React, { useState } from "react"
import { MessageSquare, MoreHorizontal, Edit2, Trash2 } from "lucide-react"
import type { TaskComment } from "@/types"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { CommentContent } from "./comment-content"
import { CommentComposer } from "./comment-composer"
import type { MentionableMember } from "./mention-autocomplete"

interface CommentItemProps {
  comment: TaskComment
  currentUserId?: string
  isAdminOrOwner?: boolean
  members: MentionableMember[]
  onReply: (parentId: string, content: string) => Promise<boolean>
  onUpdate: (commentId: string, content: string, version: number) => Promise<boolean>
  onDelete: (commentId: string) => Promise<boolean>
  isChild?: boolean
}

export const CommentItem: React.FC<CommentItemProps> = ({
  comment,
  currentUserId,
  isAdminOrOwner = false,
  members,
  onReply,
  onUpdate,
  onDelete,
  isChild = false,
}) => {
  const [isReplying, setIsReplying] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState(comment.content)
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  const isAuthor = Boolean(currentUserId && comment.author_id === currentUserId)
  const canDelete = isAuthor || isAdminOrOwner
  const canEdit = isAuthor && !comment.is_deleted

  const isEdited =
    !comment.is_deleted &&
    new Date(comment.updated_at).getTime() - new Date(comment.created_at).getTime() > 1000

  const authorName = comment.author?.full_name || comment.author?.email?.split("@")[0] || "User"
  const initials = authorName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  const timeAgo = (dateStr: string) => {
    try {
      const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
      if (seconds < 60) return "just now"
      const minutes = Math.floor(seconds / 60)
      if (minutes < 60) return `${minutes}m ago`
      const hours = Math.floor(minutes / 60)
      if (hours < 24) return `${hours}h ago`
      const days = Math.floor(hours / 24)
      return `${days}d ago`
    } catch {
      return dateStr
    }
  }

  const handleSaveEdit = async () => {
    const trimmed = editContent.trim()
    if (!trimmed || isSavingEdit) return

    setIsSavingEdit(true)
    setEditError(null)
    try {
      const ok = await onUpdate(comment.id, trimmed, comment.version)
      if (ok) {
        setIsEditing(false)
      }
    } catch (err: any) {
      setEditError(err.message || "Failed to update comment. Please refresh.")
    } finally {
      setIsSavingEdit(false)
    }
  }

  const handleDelete = async () => {
    if (window.confirm("Are you sure you want to delete this comment?")) {
      await onDelete(comment.id)
    }
  }

  return (
    <div className={`group/comment relative ${isChild ? "ml-8 mt-2.5 pl-3 border-l-2 border-border/40" : "mt-3.5"}`}>
      <div className="flex items-start gap-2.5">
        {/* Avatar */}
        <Avatar className="h-6 w-6 shrink-0 text-[10px] mt-0.5">
          <AvatarFallback className="bg-primary/15 text-primary font-medium">
            {comment.is_deleted ? "?" : initials}
          </AvatarFallback>
        </Avatar>

        {/* Comment Body */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-foreground">
                {comment.is_deleted ? "Deleted comment" : authorName}
              </span>
              <span className="text-[10px] text-muted-foreground/70">
                {timeAgo(comment.created_at)}
              </span>
              {isEdited && (
                <span className="text-[10px] text-muted-foreground/50 italic">
                  (edited)
                </span>
              )}
              {comment.isPending && (
                <span className="text-[9px] font-medium text-amber-500 bg-amber-500/10 px-1 rounded">
                  sending...
                </span>
              )}
            </div>

            {/* Actions Menu */}
            {!comment.is_deleted && (canEdit || canDelete) && !isEditing && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover/comment:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-32 p-1">
                  {canEdit && (
                    <DropdownMenuItem
                      onClick={() => {
                        setEditContent(comment.content)
                        setIsEditing(true)
                      }}
                      className="text-xs cursor-pointer gap-2"
                    >
                      <Edit2 className="h-3 w-3" />
                      <span>Edit</span>
                    </DropdownMenuItem>
                  )}
                  {canDelete && (
                    <DropdownMenuItem
                      onClick={handleDelete}
                      className="text-xs cursor-pointer text-destructive focus:text-destructive gap-2"
                    >
                      <Trash2 className="h-3 w-3" />
                      <span>Delete</span>
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* Content or Edit Box */}
          {isEditing ? (
            <div className="mt-1.5 space-y-2">
              {editError && (
                <div className="rounded bg-destructive/10 p-1.5 text-[11px] text-destructive border border-destructive/20">
                  {editError}
                </div>
              )}
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-input bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed"
              />
              <div className="flex items-center justify-end gap-1.5">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsEditing(false)}
                  disabled={isSavingEdit}
                  className="h-6 text-[11px] px-2"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveEdit}
                  disabled={!editContent.trim() || isSavingEdit}
                  className="h-6 text-[11px] px-2.5"
                >
                  {isSavingEdit ? "Saving..." : "Save"}
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-1">
              <CommentContent content={comment.content} isDeleted={comment.is_deleted} />
            </div>
          )}

          {/* Reply Action Trigger (only on top-level comments) */}
          {!isChild && !comment.is_deleted && !isEditing && (
            <div className="mt-1 flex items-center gap-3">
              <button
                onClick={() => setIsReplying(!isReplying)}
                className="text-[11px] font-medium text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
              >
                <MessageSquare className="h-3 w-3" />
                <span>{isReplying ? "Cancel reply" : "Reply"}</span>
              </button>
            </div>
          )}

          {/* Inline Reply Composer */}
          {isReplying && (
            <div className="mt-2.5">
              <CommentComposer
                onSubmit={async (content) => {
                  const ok = await onReply(comment.id, content)
                  if (ok) setIsReplying(false)
                  return ok
                }}
                members={members}
                placeholder={`Reply to ${authorName}...`}
                submitLabel="Reply"
                onCancel={() => setIsReplying(false)}
                autoFocus
              />
            </div>
          )}

          {/* Nested Replies (1-level) */}
          {comment.replies && comment.replies.length > 0 && (
            <div className="space-y-1.5">
              {comment.replies.map((reply) => (
                <CommentItem
                  key={reply.id}
                  comment={reply}
                  currentUserId={currentUserId}
                  isAdminOrOwner={isAdminOrOwner}
                  members={members}
                  onReply={onReply}
                  onUpdate={onUpdate}
                  onDelete={onDelete}
                  isChild={true}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

