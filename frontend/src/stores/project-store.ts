import { create } from "zustand"
import type { Project, BoardData, Task, TaskStatus, RoadmapMilestone } from "@/types"
import { apiClient } from "@/services/api"

interface ProjectState {
  projects: Project[]
  activeProject: Project | null
  board: BoardData | null
  roadmap: RoadmapMilestone[]
  isLoadingProjects: boolean
  isLoadingBoard: boolean
  isLoadingRoadmap: boolean
  error: string | null
  conflictMessage: string | null

  fetchProjects: (workspaceId: string) => Promise<void>
  setActiveProject: (project: Project | null) => void
  createProject: (
    workspaceId: string,
    data: { name: string; key: string; description?: string; is_private?: boolean; lead_id?: string }
  ) => Promise<Project>
  updateProject: (
    projectId: string,
    data: { name?: string; description?: string; is_private?: boolean; status?: string; lead_id?: string }
  ) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>

  // Board & Tasks
  fetchBoard: (projectId: string) => Promise<void>
  createTask: (
    projectId: string,
    data: {
      title: string
      status_id?: string
      priority?: string
      description_md?: string
      due_date?: string | null
      assignee_ids?: string[]
    }
  ) => Promise<Task>
  updateTask: (
    taskId: string,
    data: {
      title?: string
      description_md?: string | null
      priority?: string
      status_id?: string
      due_date?: string | null
      assignee_ids?: string[]
    }
  ) => Promise<Task>
  deleteTask: (taskId: string) => Promise<void>
  moveTask: (
    taskId: string,
    destinationStatusId: string,
    prevTaskId: string | null,
    nextTaskId: string | null
  ) => Promise<boolean>

  // Status Columns
  createColumn: (projectId: string, data: { name: string; color_hex?: string }) => Promise<void>
  updateColumn: (projectId: string, columnId: string, data: { name?: string; color_hex?: string }) => Promise<void>
  deleteColumn: (projectId: string, columnId: string, fallbackStatusId: string) => Promise<void>

  // Roadmap
  fetchRoadmap: (projectId: string) => Promise<void>
  clearConflictMessage: () => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  activeProject: null,
  board: null,
  roadmap: [],
  isLoadingProjects: false,
  isLoadingBoard: false,
  isLoadingRoadmap: false,
  error: null,
  conflictMessage: null,

  fetchProjects: async (workspaceId: string) => {
    set({ isLoadingProjects: true, error: null })
    try {
      const res = await apiClient.request<Project[]>(`/workspaces/${workspaceId}/projects`)
      if (res.success && res.data) {
        set({ projects: res.data })
        // If no active project selected, set the first one
        const current = get().activeProject
        if (!current && res.data.length > 0) {
          set({ activeProject: res.data[0] })
        } else if (current) {
          const match = res.data.find((p) => p.id === current.id)
          set({ activeProject: match || (res.data.length > 0 ? res.data[0] : null) })
        }
      }
    } catch (err: any) {
      set({ error: err.message || "Failed to load projects" })
    } finally {
      set({ isLoadingProjects: false })
    }
  },

  setActiveProject: (project: Project | null) => {
    set({ activeProject: project, board: null, roadmap: [] })
    if (project) {
      get().fetchBoard(project.id)
    }
  },

  createProject: async (workspaceId, data) => {
    const res = await apiClient.request<Project>(`/workspaces/${workspaceId}/projects`, {
      method: "POST",
      body: JSON.stringify(data),
    })
    if (!res.success || !res.data) {
      throw new Error(res.error?.message || "Failed to create project")
    }
    const newProj = res.data
    set((state) => ({
      projects: [newProj, ...state.projects],
      activeProject: newProj,
    }))
    return newProj
  },

  updateProject: async (projectId, data) => {
    const res = await apiClient.request<Project>(`/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
    if (!res.success || !res.data) {
      throw new Error(res.error?.message || "Failed to update project")
    }
    const updated = res.data
    set((state) => ({
      projects: state.projects.map((p) => (p.id === projectId ? updated : p)),
      activeProject: state.activeProject?.id === projectId ? updated : state.activeProject,
    }))
  },

  deleteProject: async (projectId) => {
    const res = await apiClient.request(`/projects/${projectId}`, {
      method: "DELETE",
    })
    if (!res.success) {
      throw new Error(res.error?.message || "Failed to delete project")
    }
    set((state) => {
      const remaining = state.projects.filter((p) => p.id !== projectId)
      return {
        projects: remaining,
        activeProject: state.activeProject?.id === projectId ? (remaining[0] || null) : state.activeProject,
        board: state.activeProject?.id === projectId ? null : state.board,
      }
    })
  },

  fetchBoard: async (projectId: string) => {
    set({ isLoadingBoard: true, error: null })
    try {
      const res = await apiClient.request<BoardData>(`/projects/${projectId}/board`)
      if (res.success && res.data) {
        set({ board: res.data })
      }
    } catch (err: any) {
      set({ error: err.message || "Failed to load Kanban board" })
    } finally {
      set({ isLoadingBoard: false })
    }
  },

  createTask: async (projectId, data) => {
    const res = await apiClient.request<Task>(`/projects/${projectId}/tasks`, {
      method: "POST",
      body: JSON.stringify(data),
    })
    if (!res.success || !res.data) {
      throw new Error(res.error?.message || "Failed to create task")
    }
    const newTask = res.data
    // Update local board
    set((state) => {
      if (!state.board) return state
      const nextCols = state.board.columns.map((col) => {
        if (col.status.id === newTask.status_id) {
          return {
            ...col,
            tasks: [...col.tasks, newTask],
          }
        }
        return col
      })
      return {
        board: {
          ...state.board,
          columns: nextCols,
        },
        projects: state.projects.map((p) =>
          p.id === projectId ? { ...p, task_counter: p.task_counter + 1 } : p
        ),
      }
    })
    return newTask
  },

  updateTask: async (taskId, data) => {
    const res = await apiClient.request<Task>(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
    if (!res.success || !res.data) {
      throw new Error(res.error?.message || "Failed to update task")
    }
    const updated = res.data
    set((state) => {
      if (!state.board) return state
      const nextCols = state.board.columns.map((col) => ({
        ...col,
        tasks: col.tasks.map((t) => (t.id === taskId ? updated : t)),
      }))
      return {
        board: { ...state.board, columns: nextCols },
      }
    })
    return updated
  },

  deleteTask: async (taskId) => {
    const res = await apiClient.request(`/tasks/${taskId}`, {
      method: "DELETE",
    })
    if (!res.success) {
      throw new Error(res.error?.message || "Failed to delete task")
    }
    set((state) => {
      if (!state.board) return state
      const nextCols = state.board.columns.map((col) => ({
        ...col,
        tasks: col.tasks.filter((t) => t.id !== taskId),
      }))
      return {
        board: { ...state.board, columns: nextCols },
      }
    })
  },

  moveTask: async (taskId, destinationStatusId, prevTaskId, nextTaskId) => {
    const currentBoard = get().board
    if (!currentBoard) return false

    // 1. Locate original task and status
    let originalTask: Task | null = null
    let sourceColId: string | null = null

    for (const col of currentBoard.columns) {
      const found = col.tasks.find((t) => t.id === taskId)
      if (found) {
        originalTask = { ...found }
        sourceColId = col.status.id
        break
      }
    }

    if (!originalTask || !sourceColId) return false

    // 2. Perform optimistic local reorder
    const snapshotBoard = JSON.parse(JSON.stringify(currentBoard)) as BoardData

    const optimisticColumns = currentBoard.columns.map((col) => {
      // Remove from source
      let colTasks = col.tasks.filter((t) => t.id !== taskId)

      // Insert into destination at correct position
      if (col.status.id === destinationStatusId) {
        const movedCopy: Task = {
          ...originalTask!,
          status_id: destinationStatusId,
          version: originalTask!.version + 1,
        }

        if (prevTaskId === null && nextTaskId === null) {
          colTasks.push(movedCopy)
        } else if (prevTaskId !== null) {
          const prevIdx = colTasks.findIndex((t) => t.id === prevTaskId)
          if (prevIdx !== -1) {
            colTasks.splice(prevIdx + 1, 0, movedCopy)
          } else {
            colTasks.push(movedCopy)
          }
        } else if (nextTaskId !== null) {
          const nextIdx = colTasks.findIndex((t) => t.id === nextTaskId)
          if (nextIdx !== -1) {
            colTasks.splice(nextIdx, 0, movedCopy)
          } else {
            colTasks.unshift(movedCopy)
          }
        }
      }

      return {
        ...col,
        tasks: colTasks,
      }
    })

    set({
      board: {
        ...currentBoard,
        columns: optimisticColumns,
      },
    })

    // 3. Dispatch to API
    try {
      const res = await apiClient.request<Task>(`/tasks/${taskId}/move`, {
        method: "PATCH",
        body: JSON.stringify({
          destination_status_id: destinationStatusId,
          prev_task_id: prevTaskId,
          next_task_id: nextTaskId,
          version: originalTask.version,
        }),
      })

      if (res.success && res.data) {
        const serverTask = res.data
        // Replace optimistic task with authoritative server task
        set((state) => {
          if (!state.board) return state
          return {
            board: {
              ...state.board,
              columns: state.board.columns.map((col) => ({
                ...col,
                tasks: col.tasks.map((t) => (t.id === taskId ? serverTask : t)),
              })),
            },
          }
        })
        return true
      } else {
        // Rollback snapshot on conflict or error
        set({
          board: snapshotBoard,
          conflictMessage: "A concurrent change was made to this task. Board has been refreshed.",
        })
        if (get().activeProject) {
          get().fetchBoard(get().activeProject!.id)
        }
        return false
      }
    } catch (err: any) {
      // 409 conflict or network failure -> rollback
      set({
        board: snapshotBoard,
        conflictMessage: "Concurrent edit conflict detected. Board state re-synchronized.",
      })
      if (get().activeProject) {
        get().fetchBoard(get().activeProject!.id)
      }
      return false
    }
  },

  createColumn: async (projectId, data) => {
    const res = await apiClient.request<TaskStatus>(`/projects/${projectId}/columns`, {
      method: "POST",
      body: JSON.stringify(data),
    })
    if (!res.success || !res.data) {
      throw new Error(res.error?.message || "Failed to create column")
    }
    const newStatus = res.data
    set((state) => {
      if (!state.board) return state
      return {
        board: {
          ...state.board,
          columns: [
            ...state.board.columns,
            {
              status: newStatus,
              tasks: [],
            },
          ],
        },
      }
    })
  },

  updateColumn: async (projectId, columnId, data) => {
    const res = await apiClient.request<TaskStatus>(`/projects/${projectId}/columns/${columnId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
    if (!res.success || !res.data) {
      throw new Error(res.error?.message || "Failed to update column")
    }
    const updated = res.data
    set((state) => {
      if (!state.board) return state
      return {
        board: {
          ...state.board,
          columns: state.board.columns.map((c) =>
            c.status.id === columnId ? { ...c, status: updated } : c
          ),
        },
      }
    })
  },

  deleteColumn: async (projectId, columnId, fallbackStatusId) => {
    const res = await apiClient.request(`/projects/${projectId}/columns/${columnId}`, {
      method: "DELETE",
      body: JSON.stringify({ fallback_status_id: fallbackStatusId }),
    })
    if (!res.success) {
      throw new Error(res.error?.message || "Failed to delete column")
    }
    // Re-fetch board to get updated task positions after remapping
    await get().fetchBoard(projectId)
  },

  fetchRoadmap: async (projectId: string) => {
    set({ isLoadingRoadmap: true })
    try {
      const res = await apiClient.request<RoadmapMilestone[]>(`/projects/${projectId}/roadmap`)
      if (res.success && res.data) {
        set({ roadmap: res.data })
      }
    } catch {
      set({ roadmap: [] })
    } finally {
      set({ isLoadingRoadmap: false })
    }
  },

  clearConflictMessage: () => set({ conflictMessage: null }),
}))
