import React, { useEffect, useState, useCallback } from "react"
import { MessageSquare, RefreshCw, AlertCircle } from "lucide-react"
import type { TaskComment, CommentPagination } from "@/types"
import { apiClient } from "@/services/api"
import { realTimeClient, type EventEnvelope } from "@/services/websocket-client"
import { useAuthStore } from "@/stores/auth-store"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { Button } from "@/components/ui/button"
import { CommentComposer } from "./comment-composer"
import { CommentItem } from "./comment-item"
import type { MentionableMember } from "./mention-autocomplete"

interface TaskDiscussionProps {
  taskId: string
  projectKey: string
  taskNumber: number
}

export const TaskDiscussion: React.FC<TaskDiscussionProps> = ({
  taskId,
}) => {
  const { user } = useAuthStore()
  const { currentWorkspace } = useWorkspaceStore()
  const [comments, setComments] = useState<TaskComment[]>([])
  const [members, setMembers] = useState<MentionableMember[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isAdminOrOwner = currentWorkspace?.role === "owner" || currentWorkspace?.role === "admin"

  // 1. Fetch workspace members for mention autocomplete
  useEffect(() => {
    if (!currentWorkspace?.id) return
    let isMounted = true

    apiClient
      .get(`/workspaces/${currentWorkspace.id}/members`)
      .then((res) => {
        if (isMounted && res.data) {
          const mapped: MentionableMember[] = res.data.map((m: any) => ({
            id: String(m.user?.id || m.user_id),
            full_name: m.user?.full_name || m.full_name || "",
            email: m.user?.email || m.email || "",
            avatar_url: m.user?.avatar_url || null,
          }))
          setMembers(mapped)
        }
      })
      .catch(() => {
        // Fallback: mock or empty members
      })

    return () => {
      isMounted = false
    }
  }, [currentWorkspace?.id])

  // 2. Fetch comments for this task
  const fetchComments = useCallback(
    async (cursor: string | null = null) => {
      if (cursor) {
        setIsLoadingMore(true)
      } else {
        setIsLoading(true)
      }
      setError(null)

      try {
        const queryParams = new URLSearchParams({ limit: "20" })
        if (cursor) queryParams.set("cursor", cursor)

        const res = await apiClient.request<CommentPagination>(
          `/tasks/${taskId}/comments?${queryParams.toString()}`
        )

        if (res.success && res.data) {
          if (cursor) {
            setComments((prev) => [...prev, ...res.data.items])
          } else {
            setComments(res.data.items)
          }
          setHasMore(res.data.has_more)
          setNextCursor(res.data.next_cursor || null)
        } else {
          setError(res.error?.message || "Failed to load comments.")
        }
      } catch (err: any) {
        setError(err.message || "Failed to connect to discussion service.")
      } finally {
        setIsLoading(false)
        setIsLoadingMore(false)
      }
    },
    [taskId]
  )

  useEffect(() => {
    fetchComments()
  }, [fetchComments])

  // 3. Real-Time WebSocket event listener
  useEffect(() => {
    const unsub = realTimeClient.onEvent((envelope: EventEnvelope) => {
      const payload = envelope.payload
      if (!payload || payload.task_id !== taskId) return

      if (envelope.event_type === "comment.created") {
        setComments((prev) => {
          // Check if comment already exists (e.g. from optimistic update)
          const exists = prev.some(
            (c) => c.id === payload.comment_id || c.replies.some((r) => r.id === payload.comment_id)
          )
          if (exists) return prev

          const incoming: TaskComment = {
            id: payload.comment_id,
            workspace_id: envelope.workspace_id,
            task_id: payload.task_id,
            author_id: payload.author_id,
            author: {
              id: payload.author_id,
              full_name: payload.author_name || "User",
            },
            parent_comment_id: payload.parent_comment_id,
            content: payload.content,
            is_deleted: false,
            version: payload.version || 1,
            created_at: payload.created_at || envelope.occurred_at,
            updated_at: payload.created_at || envelope.occurred_at,
            reply_count: 0,
            replies: [],
            mentions: [],
          }

          if (payload.parent_comment_id) {
            return prev.map((c) => {
              if (c.id === payload.parent_comment_id) {
                return {
                  ...c,
                  reply_count: c.reply_count + 1,
                  replies: [...c.replies, incoming],
                }
              }
              return c
            })
          } else {
            return [...prev, incoming]
          }
        })
      } else if (envelope.event_type === "comment.updated") {
        setComments((prev) =>
          prev.map((c) => {
            if (c.id === payload.comment_id) {
              if (payload.version !== undefined && payload.version < c.version) return c
              return {
                ...c,
                content: payload.content,
                version: payload.version ?? c.version + 1,
                updated_at: payload.updated_at || new Date().toISOString(),
              }
            }
            if (c.replies.some((r) => r.id === payload.comment_id)) {
              return {
                ...c,
                replies: c.replies.map((r) => {
                  if (r.id === payload.comment_id) {
                    if (payload.version !== undefined && payload.version < r.version) return r
                    return {
                      ...r,
                      content: payload.content,
                      version: payload.version ?? r.version + 1,
                      updated_at: payload.updated_at || new Date().toISOString(),
                    }
                  }
                  return r
                }),
              }
            }
            return c
          })
        )
      } else if (envelope.event_type === "comment.deleted") {
        setComments((prev) =>
          prev.map((c) => {
            if (c.id === payload.comment_id) {
              return {
                ...c,
                content: "[This comment has been deleted.]",
                is_deleted: true,
                author: null,
              }
            }
            if (c.replies.some((r) => r.id === payload.comment_id)) {
              return {
                ...c,
                replies: c.replies.map((r) =>
                  r.id === payload.comment_id
                    ? {
                        ...r,
                        content: "[This comment has been deleted.]",
                        is_deleted: true,
                        author: null,
                      }
                    : r
                ),
              }
            }
            return c
          })
        )
      }
    })

    return () => unsub()
  }, [taskId])

  // 4. Create comment (top-level or reply)
  const handleCreateComment = async (content: string, parentId: string | null = null) => {
    // Optimistic comment creation
    const tempId = `temp-${Date.now()}`
    const optimisticComment: TaskComment = {
      id: tempId,
      workspace_id: currentWorkspace?.id || "",
      task_id: taskId,
      author_id: user?.id || null,
      author: {
        id: user?.id || "",
        full_name: user?.full_name || user?.name || "You",
        email: user?.email,
      },
      parent_comment_id: parentId,
      content,
      is_deleted: false,
      version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      reply_count: 0,
      replies: [],
      mentions: [],
      isPending: true,
    }

    if (parentId) {
      setComments((prev) =>
        prev.map((c) =>
          c.id === parentId
            ? { ...c, reply_count: c.reply_count + 1, replies: [...c.replies, optimisticComment] }
            : c
        )
      )
    } else {
      setComments((prev) => [...prev, optimisticComment])
    }

    try {
      const res = await apiClient.request<TaskComment>(`/tasks/${taskId}/comments`, {
        method: "POST",
        body: JSON.stringify({
          content,
          parent_comment_id: parentId,
        }),
      })

      if (res.success && res.data) {
        const authoritative = res.data
        if (parentId) {
          setComments((prev) =>
            prev.map((c) =>
              c.id === parentId
                ? {
                    ...c,
                    replies: c.replies.map((r) => (r.id === tempId ? authoritative : r)),
                  }
                : c
            )
          )
        } else {
          setComments((prev) =>
            prev.map((c) => (c.id === tempId ? authoritative : c))
          )
        }
        return true
      } else {
        throw new Error(res.error?.message || "Failed to post comment.")
      }
    } catch (err: any) {
      // Revert optimistic comment
      if (parentId) {
        setComments((prev) =>
          prev.map((c) =>
            c.id === parentId
              ? {
                  ...c,
                  reply_count: Math.max(0, c.reply_count - 1),
                  replies: c.replies.filter((r) => r.id !== tempId),
                }
              : c
          )
        )
      } else {
        setComments((prev) => prev.filter((c) => c.id !== tempId))
      }
      throw err
    }
  }

  // 5. Update comment
  const handleUpdateComment = async (commentId: string, content: string, version: number) => {
    try {
      const res = await apiClient.request<TaskComment>(`/comments/${commentId}`, {
        method: "PATCH",
        body: JSON.stringify({ content, version }),
      })

      if (res.success && res.data) {
        const updated = res.data
        setComments((prev) =>
          prev.map((c) => {
            if (c.id === commentId) {
              return { ...c, ...updated }
            }
            return {
              ...c,
              replies: c.replies.map((r) => (r.id === commentId ? { ...r, ...updated } : r)),
            }
          })
        )
        return true
      } else {
        throw new Error(res.error?.message || "Failed to update comment.")
      }
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes("COMMENT_VERSION_CONFLICT")) {
        alert("This comment was edited concurrently by another session. Refetching discussion.")
        fetchComments()
      }
      throw err
    }
  }

  // 6. Delete comment
  const handleDeleteComment = async (commentId: string) => {
    try {
      const res = await apiClient.request(`/comments/${commentId}`, {
        method: "DELETE",
      })

      if (res.success) {
        setComments((prev) =>
          prev.map((c) => {
            if (c.id === commentId) {
              return {
                ...c,
                content: "[This comment has been deleted.]",
                is_deleted: true,
                author: null,
              }
            }
            return {
              ...c,
              replies: c.replies.map((r) =>
                r.id === commentId
                  ? {
                      ...r,
                      content: "[This comment has been deleted.]",
                      is_deleted: true,
                      author: null,
                    }
                  : r
              ),
            }
          })
        )
        return true
      }
      return false
    } catch (err: any) {
      alert(err.message || "Failed to delete comment.")
      return false
    }
  }

  const totalCommentCount = comments.reduce(
    (acc, curr) => acc + 1 + (curr.replies ? curr.replies.length : 0),
    0
  )

  return (
    <div className="space-y-4 pt-3 border-t border-border/40">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-xs font-semibold text-foreground tracking-tight">Activity & Discussion</h3>
          <span className="rounded-full bg-muted px-2 py-0.2 text-[10px] font-bold text-muted-foreground">
            {totalCommentCount}
          </span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => fetchComments()}
          disabled={isLoading}
          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
          title="Refresh discussion"
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Top Composer */}
      <CommentComposer
        onSubmit={(content) => handleCreateComment(content)}
        members={members}
        placeholder="Write a comment or mention team members with @..."
        submitLabel="Comment"
      />

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-2 text-xs text-destructive border border-destructive/20">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Comments List */}
      {isLoading && comments.length === 0 ? (
        <div className="py-6 text-center text-xs text-muted-foreground">
          <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2" />
          Loading discussion...
        </div>
      ) : comments.length === 0 ? (
        <div className="rounded-md border border-dashed border-border/50 py-8 text-center">
          <p className="text-xs text-muted-foreground">
            No comments yet. Mention your team with @ to collaborate.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              currentUserId={user?.id}
              isAdminOrOwner={isAdminOrOwner}
              members={members}
              onReply={(parentId, content) => handleCreateComment(content, parentId)}
              onUpdate={handleUpdateComment}
              onDelete={handleDeleteComment}
            />
          ))}

          {/* Load More Button */}
          {hasMore && (
            <div className="pt-2 text-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchComments(nextCursor)}
                disabled={isLoadingMore}
                className="text-xs h-7 px-3 text-muted-foreground"
              >
                {isLoadingMore ? "Loading earlier comments..." : "Load earlier comments"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

