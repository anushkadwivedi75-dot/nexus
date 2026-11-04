import React from "react"
import { useDroppable } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { Plus, MoreVertical, Trash2, Edit2 } from "lucide-react"
import type { BoardColumn, Task } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { TaskCard } from "./task-card"

interface KanbanColumnProps {
  column: BoardColumn
  projectKey: string
  onAddTask: (statusId: string) => void
  onTaskClick: (task: Task) => void
  onEditColumn: (column: BoardColumn) => void
  onDeleteColumn: (column: BoardColumn) => void
}

export const KanbanColumn: React.FC<KanbanColumnProps> = ({
  column,
  projectKey,
  onAddTask,
  onTaskClick,
  onEditColumn,
  onDeleteColumn,
}) => {
  const { setNodeRef, isOver } = useDroppable({
    id: column.status.id,
    data: {
      type: "Column",
      column,
    },
  })

  const taskIds = column.tasks.map((t) => t.id)

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col w-72 shrink-0 rounded-xl border bg-card/40 backdrop-blur-sm transition-colors ${
        isOver ? "border-primary/60 bg-accent/20" : "border-border/70"
      }`}
    >
      {/* Column Header */}
      <div className="flex items-center justify-between p-3 border-b border-border/40">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="h-2.5 w-2.5 rounded-full shrink-0"
            style={{ backgroundColor: column.status.color_hex || "#3B82F6" }}
          />
          <h3 className="font-semibold text-xs text-foreground truncate">
            {column.status.name}
          </h3>
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 min-w-[1.25rem] justify-center bg-secondary/80 text-muted-foreground"
          >
            {column.tasks.length}
          </Badge>
        </div>

        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-foreground"
            onClick={() => onAddTask(column.status.id)}
            title="Add task to column"
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-foreground"
              >
                <MoreVertical className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-36">
              <DropdownMenuItem
                className="text-xs gap-2 cursor-pointer"
                onClick={() => onEditColumn(column)}
              >
                <Edit2 className="h-3.5 w-3.5 text-muted-foreground" />
                Edit Column
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-xs gap-2 text-destructive focus:text-destructive cursor-pointer"
                onClick={() => onDeleteColumn(column)}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete Column
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Task List / Drop Zone */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[calc(100vh-16rem)] min-h-[140px]">
        <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
          {column.tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              projectKey={projectKey}
              onClick={() => onTaskClick(task)}
            />
          ))}
        </SortableContext>

        {column.tasks.length === 0 && (
          <div className="h-28 rounded-lg border border-dashed border-border/50 flex flex-col items-center justify-center text-muted-foreground/60 text-xs p-3 text-center">
            <span>No tasks in this status</span>
            <Button
              variant="link"
              size="sm"
              className="text-xs h-auto p-0 mt-1 text-primary"
              onClick={() => onAddTask(column.status.id)}
            >
              + Create task
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

