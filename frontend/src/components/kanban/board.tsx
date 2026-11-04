import React, { useState } from "react"
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  closestCorners,
} from "@dnd-kit/core"
import { Plus, AlertTriangle, X } from "lucide-react"
import type { BoardColumn, Task, Project } from "@/types"
import { useProjectStore } from "@/stores/project-store"
import { Button } from "@/components/ui/button"
import { KanbanColumn } from "./column"
import { TaskCard } from "./task-card"
import { TaskModal } from "./task-modal"
import { TaskCreateDialog } from "./task-create-dialog"
import { CreateColumnDialog, DeleteColumnDialog } from "./column-modals"

interface KanbanBoardProps {
  project: Project
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({ project }) => {
  const {
    board,
    isLoadingBoard,
    moveTask,
    createTask,
    updateTask,
    deleteTask,
    createColumn,
    deleteColumn,
    conflictMessage,
    clearConflictMessage,
  } = useProjectStore()

  // Drag-and-drop state
  const [activeTask, setActiveTask] = useState<Task | null>(null)

  // Dialog states
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false)
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false)
  const [createTaskStatusId, setCreateTaskStatusId] = useState<string | undefined>(undefined)

  const [isCreateColumnOpen, setIsCreateColumnOpen] = useState(false)
  const [columnToDelete, setColumnToDelete] = useState<BoardColumn | null>(null)
  const [isDeleteColumnOpen, setIsDeleteColumnOpen] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // 5px movement required to trigger drag (prevents accidental clicks)
      },
    })
  )

  if (isLoadingBoard && !board) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!board) {
    return (
      <div className="rounded-lg border border-border/60 p-8 text-center text-muted-foreground text-xs">
        No board data available for this project.
      </div>
    )
  }

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const task = findTaskById(active.id as string)
    if (task) {
      setActiveTask(task)
    }
  }

  const findTaskById = (taskId: string): Task | null => {
    if (!board) return null
    for (const col of board.columns) {
      const match = col.tasks.find((t) => t.id === taskId)
      if (match) return match
    }
    return null
  }

  const findColumnByStatusOrTaskId = (id: string): BoardColumn | null => {
    if (!board) return null
    // 1. Direct status column match
    const colMatch = board.columns.find((c) => c.status.id === id)
    if (colMatch) return colMatch

    // 2. Task parent column match
    for (const col of board.columns) {
      if (col.tasks.some((t) => t.id === id)) {
        return col
      }
    }
    return null
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    setActiveTask(null)

    if (!over) return

    const activeId = active.id as string
    const overId = over.id as string

    if (activeId === overId) return

    const sourceCol = findColumnByStatusOrTaskId(activeId)
    const destCol = findColumnByStatusOrTaskId(overId)

    if (!sourceCol || !destCol) return

    const destinationStatusId = destCol.status.id
    const destTasks = destCol.tasks

    // Calculate prev_task_id and next_task_id in target position
    let prevTaskId: string | null = null
    let nextTaskId: string | null = null

    // Check if dropped directly on another task
    const overTaskIndex = destTasks.findIndex((t) => t.id === overId)

    if (overTaskIndex !== -1) {
      // Dropped on/near an existing task in dest column
      if (sourceCol.status.id === destCol.status.id) {
        // Reordering within the same column
        const oldIndex = destTasks.findIndex((t) => t.id === activeId)
        if (oldIndex < overTaskIndex) {
          // Moved down
          prevTaskId = destTasks[overTaskIndex]?.id || null
          nextTaskId = destTasks[overTaskIndex + 1]?.id || null
        } else {
          // Moved up
          prevTaskId = destTasks[overTaskIndex - 1]?.id || null
          nextTaskId = destTasks[overTaskIndex]?.id || null
        }
      } else {
        // Cross-column drop onto a task
        prevTaskId = destTasks[overTaskIndex - 1]?.id || null
        nextTaskId = destTasks[overTaskIndex]?.id || null
      }
    } else {
      // Dropped onto the column container itself
      if (destTasks.length > 0) {
        prevTaskId = destTasks[destTasks.length - 1].id
        nextTaskId = null
      }
    }

    await moveTask(activeId, destinationStatusId, prevTaskId, nextTaskId)
  }

  const allStatuses = board.columns.map((c) => c.status)

  return (
    <div className="space-y-4">
      {/* Concurrency Conflict Banner */}
      {conflictMessage && (
        <div className="flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-400">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{conflictMessage}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 text-amber-400 hover:text-amber-200"
            onClick={clearConflictMessage}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {/* Board Columns Container */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-4 pt-1 items-start min-h-[calc(100vh-14rem)]">
          {board.columns.map((column) => (
            <KanbanColumn
              key={column.status.id}
              column={column}
              projectKey={project.key}
              onAddTask={(statusId) => {
                setCreateTaskStatusId(statusId)
                setIsCreateTaskOpen(true)
              }}
              onTaskClick={(task) => {
                setSelectedTask(task)
                setIsTaskModalOpen(true)
              }}
              onEditColumn={(_col) => {
                // Future column renaming
              }}
              onDeleteColumn={(col) => {
                if (board.columns.length <= 1) {
                  alert("Cannot delete the only status column in a project.")
                  return
                }
                setColumnToDelete(col)
                setIsDeleteColumnOpen(true)
              }}
            />
          ))}

          {/* Add Status Column Button */}
          <div className="w-72 shrink-0">
            <Button
              variant="outline"
              className="w-full h-11 border-dashed border-border/80 text-muted-foreground hover:text-foreground text-xs justify-start gap-2 bg-card/20 hover:bg-card/40"
              onClick={() => setIsCreateColumnOpen(true)}
            >
              <Plus className="h-4 w-4" />
              Add Status Column
            </Button>
          </div>
        </div>

        {/* Drag Overlay for smooth visual feedback */}
        <DragOverlay>
          {activeTask ? (
            <div className="w-72 rotate-1 scale-105 shadow-2xl opacity-90 cursor-grabbing">
              <TaskCard
                task={activeTask}
                projectKey={project.key}
                onClick={() => {}}
              />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Task Details / Edit Modal */}
      <TaskModal
        task={selectedTask}
        projectKey={project.key}
        statuses={allStatuses}
        isOpen={isTaskModalOpen}
        onClose={() => {
          setIsTaskModalOpen(false)
          setSelectedTask(null)
        }}
        onUpdate={async (taskId, updates) => {
          await updateTask(taskId, updates)
        }}
        onDelete={async (taskId) => {
          await deleteTask(taskId)
        }}
      />

      {/* Task Creation Dialog */}
      <TaskCreateDialog
        isOpen={isCreateTaskOpen}
        defaultStatusId={createTaskStatusId}
        statuses={allStatuses}
        onClose={() => setIsCreateTaskOpen(false)}
        onCreate={async (data) => {
          await createTask(project.id, data)
        }}
      />

      {/* Column Creation Dialog */}
      <CreateColumnDialog
        isOpen={isCreateColumnOpen}
        onClose={() => setIsCreateColumnOpen(false)}
        onCreate={async (data) => {
          await createColumn(project.id, data)
        }}
      />

      {/* Column Deletion Dialog with Task Remapping */}
      <DeleteColumnDialog
        column={columnToDelete}
        allColumns={board.columns}
        isOpen={isDeleteColumnOpen}
        onClose={() => {
          setIsDeleteColumnOpen(false)
          setColumnToDelete(null)
        }}
        onDelete={async (columnId, fallbackId) => {
          await deleteColumn(project.id, columnId, fallbackId)
        }}
      />
    </div>
  )
}
