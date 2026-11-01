import { create } from "zustand"
import type { Workspace } from "@/types"
import { mockWorkspaces } from "@/data/mock-data"

interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspace: Workspace
  isSidebarCollapsed: boolean
  isCommandPaletteOpen: boolean
  isMobileSidebarOpen: boolean
  setWorkspace: (workspaceId: string) => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setCommandPaletteOpen: (open: boolean) => void
  setMobileSidebarOpen: (open: boolean) => void
  addMockWorkspace: (name: string, slug: string) => void
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  workspaces: mockWorkspaces,
  currentWorkspace: mockWorkspaces[0],
  isSidebarCollapsed: false,
  isCommandPaletteOpen: false,
  isMobileSidebarOpen: false,

  setWorkspace: (workspaceId: string) =>
    set((state) => {
      const found = state.workspaces.find((w) => w.id === workspaceId)
      return found ? { currentWorkspace: found } : state
    }),

  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

  setSidebarCollapsed: (collapsed: boolean) =>
    set({ isSidebarCollapsed: collapsed }),

  setCommandPaletteOpen: (open: boolean) =>
    set({ isCommandPaletteOpen: open }),

  setMobileSidebarOpen: (open: boolean) =>
    set({ isMobileSidebarOpen: open }),

  addMockWorkspace: (name: string, slug: string) =>
    set((state) => {
      const initials = name
        .split(" ")
        .map((p) => p[0])
        .join("")
        .toUpperCase()
        .slice(0, 2) || "NW"

      const newWs: Workspace = {
        id: `ws-${Date.now()}`,
        name,
        slug: slug.toLowerCase().replace(/\s+/g, "-"),
        plan: "Starter",
        role: "owner",
        membersCount: 1,
        colorHex: "#8B5CF6",
        initials,
      }
      return {
        workspaces: [...state.workspaces, newWs],
        currentWorkspace: newWs,
      }
    }),
}))
