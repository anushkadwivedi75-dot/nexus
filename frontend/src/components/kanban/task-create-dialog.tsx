import React, { useState } from "react"
import type { TaskStatus } from "@/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface TaskCreateDialogProps {
  isOpen: boolean
  defaultStatusId?: string
  statuses: TaskStatus[]
  onClose: () => void
  onCreate: (data: {
    title: string
    status_id?: string
    priority?: string
    description_md?: string
    due_date?: string | null
  }) => Promise<void>
}

export const TaskCreateDialog: React.FC<TaskCreateDialogProps> = ({
  isOpen,
  defaultStatusId,
  statuses,
  onClose,
  onCreate,
}) => {
  const [title, setTitle] = useState("")
  const [statusId, setStatusId] = useState(defaultStatusId || (statuses[0]?.id ?? ""))
  const [priority, setPriority] = useState("medium")
  const [dueDate, setDueDate] = useState("")
  const [descriptionMd, setDescriptionMd] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Keep statusId in sync when defaultStatusId changes
  React.useEffect(() => {
    if (defaultStatusId) setStatusId(defaultStatusId)
    else if (statuses.length > 0) setStatusId(statuses[0].id)
  }, [defaultStatusId, statuses])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      setError("Task title is required")
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await onCreate({
        title: title.trim(),
        status_id: statusId || undefined,
        priority,
        description_md: descriptionMd.trim() || undefined,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
      })
      setTitle("")
      setDescriptionMd("")
      setDueDate("")
      onClose()
    } catch (err: any) {
      setError(err.message || "Failed to create task")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border/80">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">Create Task</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Add a new task to your project board with atomic sequential numbering.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mt-3 rounded-md bg-destructive/15 p-2 text-xs text-destructive border border-destructive/20">
              {error}
            </div>
          )}

          <div className="space-y-3 py-3 text-xs">
            <div>
              <label className="text-muted-foreground block mb-1">Title *</label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What needs to be done?"
                autoFocus
                className="h-8 text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-muted-foreground block mb-1">Status Column</label>
                <select
                  value={statusId}
                  onChange={(e) => setStatusId(e.target.value)}
                  className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {statuses.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-muted-foreground block mb-1">Priority</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary capitalize"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-muted-foreground block mb-1">Due Date</label>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div>
              <label className="text-muted-foreground block mb-1">Description (Markdown)</label>
              <textarea
                value={descriptionMd}
                onChange={(e) => setDescriptionMd(e.target.value)}
                placeholder="Specifications, links, notes..."
                rows={3}
                className="w-full rounded-md border border-input bg-background p-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            </div>
          </div>

          <DialogFooter className="border-t border-border/40 pt-3">
            <Button type="button" variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting} className="text-xs h-8">
              {isSubmitting ? "Creating..." : "Create Task"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

