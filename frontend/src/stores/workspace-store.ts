import { create } from "zustand"
import type { Workspace } from "@/types"
import { apiClient } from "@/services/api"
import { mockWorkspaces } from "@/data/mock-data"

const COLOR_PALETTE = ["#8B5CF6", "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#6366F1"]

function formatWorkspaceItem(raw: any, index: number = 0): Workspace {
  const name = raw.name || "Workspace"
  const initials =
    name
      .split(" ")
      .map((p: string) => p[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "WS"

  return {
    id: String(raw.id),
    name: raw.name,
    slug: raw.slug,
    plan: raw.plan || "Starter",
    role: raw.role || "member",
    membersCount: raw.members_count || raw.membersCount || 1,
    members_count: raw.members_count || raw.membersCount || 1,
    colorHex: raw.colorHex || COLOR_PALETTE[index % COLOR_PALETTE.length],
    initials,
    owner_id: raw.owner_id ? String(raw.owner_id) : undefined,
    logo_url: raw.logo_url || null,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  }
}

interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspace: Workspace
  isLoading: boolean
  error: string | null
  isSidebarCollapsed: boolean
  isCommandPaletteOpen: boolean
  isMobileSidebarOpen: boolean

  fetchWorkspaces: () => Promise<void>
  setWorkspace: (workspaceId: string) => void
  createWorkspace: (name: string, slug: string) => Promise<Workspace>
  updateWorkspace: (workspaceId: string, data: { name?: string; slug?: string; logo_url?: string }) => Promise<void>
  deleteWorkspace: (workspaceId: string) => Promise<void>
  transferOwnership: (workspaceId: string, newOwnerId: string) => Promise<void>
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setCommandPaletteOpen: (open: boolean) => void
  setMobileSidebarOpen: (open: boolean) => void
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: mockWorkspaces,
  currentWorkspace: mockWorkspaces[0],
  isLoading: false,
  error: null,
  isSidebarCollapsed: false,
  isCommandPaletteOpen: false,
  isMobileSidebarOpen: false,

  fetchWorkspaces: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.get("/workspaces")
      const list = res.data || []
      if (list.length > 0) {
        const formatted = list.map((item: any, i: number) => formatWorkspaceItem(item, i))
        const savedId = typeof localStorage !== "undefined" ? localStorage.getItem("current_workspace_id") : null
        const active = formatted.find((w: Workspace) => w.id === savedId) || formatted[0]

        set({
          workspaces: formatted,
          currentWorkspace: active,
          isLoading: false,
        })
      } else {
        set({ isLoading: false })
      }
    } catch (err: any) {
      console.warn("[WorkspaceStore] Failed to fetch workspaces from API, using fallback:", err)
      set({ isLoading: false })
    }
  },

  setWorkspace: (workspaceId: string) => {
    const found = get().workspaces.find((w) => w.id === workspaceId)
    if (found) {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem("current_workspace_id", workspaceId)
      }
      set({ currentWorkspace: found })
    }
  },

  createWorkspace: async (name: string, slug: string) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.post("/workspaces", { name, slug })
      const created = formatWorkspaceItem(res.data, get().workspaces.length)
      const updatedList = [created, ...get().workspaces]

      if (typeof localStorage !== "undefined") {
        localStorage.setItem("current_workspace_id", created.id)
      }

      set({
        workspaces: updatedList,
        currentWorkspace: created,
        isLoading: false,
      })
      return created
    } catch (err: any) {
      const msg = err.data?.detail || err.message || "Failed to create workspace."
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  updateWorkspace: async (workspaceId: string, data) => {
    set({ isLoading: true, error: null })
    try {
      const res = await apiClient.patch(`/workspaces/${workspaceId}`, data)
      const updated = formatWorkspaceItem(res.data)

      set((state) => {
        const newWorkspaces = state.workspaces.map((w) => (w.id === workspaceId ? { ...w, ...updated } : w))
        const newCurrent = state.currentWorkspace.id === workspaceId ? { ...state.currentWorkspace, ...updated } : state.currentWorkspace
        return {
          workspaces: newWorkspaces,
          currentWorkspace: newCurrent,
          isLoading: false,
        }
      })
    } catch (err: any) {
      const msg = err.data?.detail || err.message || "Failed to update workspace."
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  deleteWorkspace: async (workspaceId: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.delete(`/workspaces/${workspaceId}`)
      set((state) => {
        const remaining = state.workspaces.filter((w) => w.id !== workspaceId)
        const nextActive = remaining[0] || mockWorkspaces[0]
        if (typeof localStorage !== "undefined") {
          localStorage.setItem("current_workspace_id", nextActive.id)
        }
        return {
          workspaces: remaining,
          currentWorkspace: nextActive,
          isLoading: false,
        }
      })
    } catch (err: any) {
      const msg = err.data?.detail || err.message || "Failed to delete workspace."
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  transferOwnership: async (workspaceId: string, newOwnerId: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post(`/workspaces/${workspaceId}/transfer-ownership`, {
        new_owner_id: newOwnerId,
      })
      await get().fetchWorkspaces()
    } catch (err: any) {
      const msg = err.data?.detail || err.message || "Failed to transfer ownership."
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

  setSidebarCollapsed: (collapsed: boolean) =>
    set({ isSidebarCollapsed: collapsed }),

  setCommandPaletteOpen: (open: boolean) =>
    set({ isCommandPaletteOpen: open }),

  setMobileSidebarOpen: (open: boolean) =>
    set({ isMobileSidebarOpen: open }),
}))
