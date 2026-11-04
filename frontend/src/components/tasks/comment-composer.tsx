import React, { useState, useRef } from "react"
import { Send, CornerDownLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MentionAutocomplete, type MentionableMember } from "./mention-autocomplete"

interface CommentComposerProps {
  onSubmit: (content: string) => Promise<boolean>
  members: MentionableMember[]
  placeholder?: string
  submitLabel?: string
  onCancel?: () => void
  autoFocus?: boolean
  className?: string
}

export const CommentComposer: React.FC<CommentComposerProps> = ({
  onSubmit,
  members,
  placeholder = "Leave a comment... Type @ to mention team members (Cmd+Enter to send)",
  submitLabel = "Comment",
  onCancel,
  autoFocus = false,
  className = "",
}) => {
  const [content, setContent] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [mentionQuery, setMentionQuery] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Track cursor and handle mention triggering
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setContent(val)
    setError(null)

    const cursorPos = e.target.selectionStart || 0
    const textBeforeCursor = val.slice(0, cursorPos)
    const atMatch = textBeforeCursor.match(/@([a-zA-Z0-9_.-]*)$/)

    if (atMatch) {
      setMentionQuery(atMatch[1])
    } else {
      setMentionQuery(null)
    }
  }

  const handleSelectMention = (member: MentionableMember) => {
    if (!textareaRef.current) return
    const cursorPos = textareaRef.current.selectionStart || 0
    const textBeforeCursor = content.slice(0, cursorPos)
    const textAfterCursor = content.slice(cursorPos)

    const atMatch = textBeforeCursor.match(/@([a-zA-Z0-9_.-]*)$/)
    if (atMatch) {
      const mentionStart = textBeforeCursor.lastIndexOf("@")
      const name = member.full_name || member.email?.split("@")[0] || "User"
      const replacement = `@[${name}](${member.id}) `
      const newContent = content.slice(0, mentionStart) + replacement + textAfterCursor
      setContent(newContent)
      setMentionQuery(null)

      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus()
          const newPos = mentionStart + replacement.length
          textareaRef.current.setSelectionRange(newPos, newPos)
        }
      }, 0)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleSubmit = async () => {
    const trimmed = content.trim()
    if (!trimmed || isSubmitting) return

    setIsSubmitting(true)
    setError(null)
    try {
      const success = await onSubmit(trimmed)
      if (success) {
        setContent("")
        setMentionQuery(null)
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit comment. Your draft has been preserved.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={`relative rounded-md border border-border/70 bg-card p-2.5 transition-colors focus-within:border-primary/60 focus-within:ring-1 focus-within:ring-primary/20 ${className}`}>
      {/* Mention Autocomplete Dropdown */}
      {mentionQuery !== null && (
        <MentionAutocomplete
          members={members}
          filterText={mentionQuery}
          onSelect={handleSelectMention}
          onClose={() => setMentionQuery(null)}
        />
      )}

      {error && (
        <div className="mb-2 rounded bg-destructive/10 px-2 py-1 text-[11px] text-destructive border border-destructive/20">
          {error}
        </div>
      )}

      <textarea
        ref={textareaRef}
        value={content}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
        rows={2}
        className="w-full resize-none border-none bg-transparent p-0 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none shadow-none leading-relaxed"
      />

      <div className="mt-2 flex items-center justify-between border-t border-border/30 pt-2">
        <span className="text-[10px] text-muted-foreground flex items-center gap-1 hidden sm:inline-flex">
          <CornerDownLeft className="h-2.5 w-2.5" />
          <span>Cmd/Ctrl + Enter to send</span>
        </span>

        <div className="flex items-center gap-1.5 ml-auto">
          {onCancel && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onCancel}
              disabled={isSubmitting}
              className="h-7 text-xs px-2 text-muted-foreground"
            >
              Cancel
            </Button>
          )}
          <Button
            type="button"
            size="sm"
            onClick={handleSubmit}
            disabled={!content.trim() || isSubmitting}
            className="h-7 text-xs px-2.5 gap-1"
          >
            <Send className="h-3 w-3" />
            <span>{isSubmitting ? "Sending..." : submitLabel}</span>
          </Button>
        </div>
      </div>
    </div>
  )
}

