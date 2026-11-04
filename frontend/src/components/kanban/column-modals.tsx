import React, { useState } from "react"
import type { BoardColumn } from "@/types"
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

const PRESET_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Emerald
  "#F59E0B", // Amber
  "#EF4444", // Red
  "#8B5CF6", // Purple
  "#EC4899", // Pink
  "#6B7280", // Gray
]

interface CreateColumnDialogProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (data: { name: string; color_hex?: string }) => Promise<void>
}

export const CreateColumnDialog: React.FC<CreateColumnDialogProps> = ({
  isOpen,
  onClose,
  onCreate,
}) => {
  const [name, setName] = useState("")
  const [colorHex, setColorHex] = useState(PRESET_COLORS[0])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError("Column name is required")
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await onCreate({ name: name.trim(), color_hex: colorHex })
      setName("")
      onClose()
    } catch (err: any) {
      setError(err.message || "Failed to create column")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-sm bg-card border-border/80">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">New Status Column</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Add a custom workflow status column to your project.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mt-3 rounded-md bg-destructive/15 p-2 text-xs text-destructive border border-destructive/20">
              {error}
            </div>
          )}

          <div className="space-y-3 py-3 text-xs">
            <div>
              <label className="text-muted-foreground block mb-1">Column Name *</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Code Review, QA, Staging"
                autoFocus
                className="h-8 text-xs"
              />
            </div>

            <div>
              <label className="text-muted-foreground block mb-1.5">Color Tag</label>
              <div className="flex items-center gap-2">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColorHex(c)}
                    className={`h-6 w-6 rounded-full border transition-all ${
                      colorHex === c ? "ring-2 ring-primary ring-offset-2 ring-offset-background scale-110" : "border-border/60 hover:scale-105"
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
          </div>

          <DialogFooter className="border-t border-border/40 pt-3">
            <Button type="button" variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting} className="text-xs h-8">
              {isSubmitting ? "Adding..." : "Add Column"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

interface DeleteColumnDialogProps {
  column: BoardColumn | null
  allColumns: BoardColumn[]
  isOpen: boolean
  onClose: () => void
  onDelete: (columnId: string, fallbackStatusId: string) => Promise<void>
}

export const DeleteColumnDialog: React.FC<DeleteColumnDialogProps> = ({
  column,
  allColumns,
  isOpen,
  onClose,
  onDelete,
}) => {
  // Other columns available as fallback
  const fallbackCandidates = column ? allColumns.filter((c) => c.status.id !== column.status.id) : []
  const [fallbackId, setFallbackId] = useState("")
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Sync fallbackId when column or candidates change
  React.useEffect(() => {
    if (fallbackCandidates.length > 0 && !fallbackId) {
      setFallbackId(fallbackCandidates[0].status.id)
    }
  }, [fallbackCandidates, fallbackId])

  if (!column) return null

  const handleDelete = async () => {
    if (!fallbackId) {
      setError("You must select a fallback status column for existing tasks.")
      return
    }
    setError(null)
    setIsDeleting(true)
    try {
      await onDelete(column.status.id, fallbackId)
      onClose()
    } catch (err: any) {
      setError(err.message || "Failed to delete column")
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border/80">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold text-destructive">
            Delete "{column.status.name}" Column
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Deleting a column requires remapping any tasks currently in this status to a fallback column to avoid orphaned references.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="mt-3 rounded-md bg-destructive/15 p-2 text-xs text-destructive border border-destructive/20">
            {error}
          </div>
        )}

        <div className="space-y-3 py-3 text-xs">
          <div className="rounded-md bg-muted/40 p-3 text-xs text-foreground">
            There {column.tasks.length === 1 ? "is" : "are"}{" "}
            <span className="font-semibold text-primary">{column.tasks.length}</span> active task{column.tasks.length === 1 ? "" : "s"} in this column.
          </div>

          <div>
            <label className="text-muted-foreground block mb-1">
              Select Fallback Status Column *
            </label>
            <select
              value={fallbackId}
              onChange={(e) => setFallbackId(e.target.value)}
              className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {fallbackCandidates.map((c) => (
                <option key={c.status.id} value={c.status.id}>
                  {c.status.name} ({c.tasks.length} tasks)
                </option>
              ))}
            </select>
          </div>
        </div>

        <DialogFooter className="border-t border-border/40 pt-3">
          <Button type="button" variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={isDeleting || !fallbackId}
            className="text-xs h-8"
          >
            {isDeleting ? "Remapping & Deleting..." : "Confirm Deletion"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
