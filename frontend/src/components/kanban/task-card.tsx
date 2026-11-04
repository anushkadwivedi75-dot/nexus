import React from "react"
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Calendar, AlertCircle, Clock, CheckCircle2 } from "lucide-react"
import type { Task } from "@/types"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

interface TaskCardProps {
  task: Task
  projectKey: string
  onClick: () => void
}

const PRIORITY_CONFIG = {
  urgent: { label: "Urgent", class: "bg-red-500/15 text-red-400 border-red-500/30", icon: AlertCircle },
  high: { label: "High", class: "bg-amber-500/15 text-amber-400 border-amber-500/30", icon: AlertCircle },
  medium: { label: "Medium", class: "bg-blue-500/15 text-blue-400 border-blue-500/30", icon: Clock },
  low: { label: "Low", class: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30", icon: CheckCircle2 },
}

export const TaskCard: React.FC<TaskCardProps> = ({ task, projectKey, onClick }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: task.id,
    data: {
      type: "Task",
      task,
    },
  })

  const style: React.CSSProperties = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.35 : 1,
  }

  const priorityMeta = PRIORITY_CONFIG[task.priority as keyof typeof PRIORITY_CONFIG] || PRIORITY_CONFIG.medium

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={`group relative rounded-lg border border-border/80 bg-card p-3 shadow-sm hover:border-primary/50 hover:shadow-md transition-all cursor-grab active:cursor-grabbing select-none ${
        isDragging ? "ring-2 ring-primary ring-offset-2 ring-offset-background" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="font-mono text-[11px] font-semibold text-muted-foreground group-hover:text-primary transition-colors">
          {projectKey}-{task.task_number}
        </span>
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 py-0 capitalize border ${priorityMeta.class}`}
        >
          {priorityMeta.label}
        </Badge>
      </div>

      <h4 className="text-xs font-medium text-foreground line-clamp-2 leading-relaxed mb-2.5">
        {task.title}
      </h4>

      <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/40">
        <div className="flex items-center gap-1.5">
          {task.due_date ? (
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Calendar className="h-3 w-3" />
              {new Date(task.due_date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground/60">No due date</span>
          )}
        </div>

        <div className="flex -space-x-1.5 overflow-hidden">
          {task.assignees && task.assignees.length > 0 ? (
            task.assignees.map((a) => (
              <Avatar key={a.user_id} className="h-5 w-5 border border-background">
                <AvatarFallback className="text-[9px] bg-secondary text-secondary-foreground">
                  {(a.full_name || a.email || "U").slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            ))
          ) : (
            <span className="text-[10px] text-muted-foreground/50">Unassigned</span>
          )}
        </div>
      </div>
    </div>
  )
}
