import React, { useState, useEffect } from "react"
import {
  Trash2,
  Save,
  Eye,
  Edit3,
} from "lucide-react"
import type { Task, TaskStatus } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface TaskModalProps {
  task: Task | null
  projectKey: string
  statuses: TaskStatus[]
  isOpen: boolean
  onClose: () => void
  onUpdate: (taskId: string, updates: Partial<Task>) => Promise<void>
  onDelete: (taskId: string) => Promise<void>
}

export const TaskModal: React.FC<TaskModalProps> = ({
  task,
  projectKey,
  statuses,
  isOpen,
  onClose,
  onUpdate,
  onDelete,
}) => {
  if (!task) return null

  const [title, setTitle] = useState(task.title)
  const [descriptionMd, setDescriptionMd] = useState(task.description_md || "")
  const [priority, setPriority] = useState(task.priority)
  const [statusId, setStatusId] = useState(task.status_id)
  const [dueDate, setDueDate] = useState(task.due_date ? task.due_date.slice(0, 10) : "")
  const [isPreview, setIsPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    setTitle(task.title)
    setDescriptionMd(task.description_md || "")
    setPriority(task.priority)
    setStatusId(task.status_id)
    setDueDate(task.due_date ? task.due_date.slice(0, 10) : "")
    setIsPreview(false)
  }, [task])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onUpdate(task.id, {
        title,
        description_md: descriptionMd,
        priority: priority as any,
        status_id: statusId,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
      })
      onClose()
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete ${projectKey}-${task.task_number}?`)) {
      return
    }
    setIsDeleting(true)
    try {
      await onDelete(task.id)
      onClose()
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-card border-border/80">
        <DialogHeader className="border-b border-border/40 pb-3">
          <div className="flex items-center justify-between pr-6">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-muted-foreground">
                {projectKey}-{task.task_number}
              </span>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 capitalize">
                v{task.version}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting}
              className="text-xs text-destructive hover:text-destructive hover:bg-destructive/10 h-7"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Delete Task
            </Button>
          </div>
          <DialogTitle className="mt-2 text-base font-semibold">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="text-base font-semibold border-none bg-transparent px-0 focus-visible:ring-0 shadow-none"
              placeholder="Task title..."
            />
          </DialogTitle>
        </DialogHeader>

        {/* Task Properties Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 py-2 text-xs border-b border-border/40">
          <div>
            <label className="text-muted-foreground block mb-1">Status</label>
            <select
              value={statusId}
              onChange={(e) => setStatusId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
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
              onChange={(e) => setPriority(e.target.value as any)}
              className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary capitalize"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>

          <div>
            <label className="text-muted-foreground block mb-1">Due Date</label>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="h-7 text-xs px-2"
            />
          </div>
        </div>

        {/* Markdown Description */}
        <div className="space-y-2 py-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-muted-foreground">Description (Markdown)</label>
            <div className="flex items-center gap-1">
              <Button
                variant={!isPreview ? "secondary" : "ghost"}
                size="sm"
                className="h-6 text-[11px] px-2"
                onClick={() => setIsPreview(false)}
              >
                <Edit3 className="h-3 w-3 mr-1" />
                Write
              </Button>
              <Button
                variant={isPreview ? "secondary" : "ghost"}
                size="sm"
                className="h-6 text-[11px] px-2"
                onClick={() => setIsPreview(true)}
              >
                <Eye className="h-3 w-3 mr-1" />
                Preview
              </Button>
            </div>
          </div>

          {!isPreview ? (
            <textarea
              value={descriptionMd}
              onChange={(e) => setDescriptionMd(e.target.value)}
              placeholder="Add details, acceptance criteria, markdown lists..."
              rows={6}
              className="w-full rounded-md border border-input bg-background/50 p-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-y"
            />
          ) : (
            <div className="min-h-[140px] max-h-[220px] overflow-y-auto rounded-md border border-input bg-muted/20 p-3 text-xs leading-relaxed text-foreground whitespace-pre-wrap">
              {descriptionMd ? descriptionMd : <span className="text-muted-foreground italic">No description provided.</span>}
            </div>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between border-t border-border/40 pt-3">
          <span className="text-[10px] text-muted-foreground">
            Created {new Date(task.created_at).toLocaleString()}
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave} disabled={isSaving} className="text-xs h-8">
              <Save className="h-3.5 w-3.5 mr-1.5" />
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
