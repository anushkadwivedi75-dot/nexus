import React, { useState, useEffect } from "react"
import { Lock, Globe, Trash2, UserPlus } from "lucide-react"
import type { Project, WorkspaceMemberItem } from "@/types"
import { apiClient } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface CreateProjectDialogProps {
  isOpen: boolean
  workspaceId: string
  onClose: () => void
  onCreate: (data: {
    name: string
    key: string
    description?: string
    is_private?: boolean
    lead_id?: string
  }) => Promise<void>
}

export const CreateProjectDialog: React.FC<CreateProjectDialogProps> = ({
  isOpen,
  workspaceId,
  onClose,
  onCreate,
}) => {
  const [name, setName] = useState("")
  const [key, setKey] = useState("")
  const [description, setDescription] = useState("")
  const [isPrivate, setIsPrivate] = useState(false)
  const [leadId, setLeadId] = useState("")
  const [members, setMembers] = useState<WorkspaceMemberItem[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      apiClient.request<WorkspaceMemberItem[]>(`/workspaces/${workspaceId}/members`).then((res) => {
        if (res.success && res.data) {
          setMembers(res.data)
        }
      }).catch(() => {})
    }
  }, [isOpen, workspaceId])

  // Auto-generate suggested key when name changes
  const handleNameChange = (val: string) => {
    setName(val)
    if (!key || key.length < 3) {
      const generated = val
        .replace(/[^a-zA-Z0-9]/g, "")
        .slice(0, 4)
        .toUpperCase()
      if (generated.length >= 2) {
        setKey(generated)
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const cleanKey = key.trim().toUpperCase()
    if (!name.trim()) {
      setError("Project name is required")
      return
    }
    if (!cleanKey || !/^[A-Z0-9]{2,10}$/.test(cleanKey)) {
      setError("Project key must be 2 to 10 uppercase alphanumeric characters (e.g. 'NEX', 'ENG1').")
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await onCreate({
        name: name.trim(),
        key: cleanKey,
        description: description.trim() || undefined,
        is_private: isPrivate,
        lead_id: leadId || undefined,
      })
      setName("")
      setKey("")
      setDescription("")
      setIsPrivate(false)
      setLeadId("")
      onClose()
    } catch (err: any) {
      setError(err.message || "Failed to create project")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border/80">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">Create New Project</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Initialize a project workspace with default status columns and an atomic 64-bit task counter.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mt-3 rounded-md bg-destructive/15 p-2 text-xs text-destructive border border-destructive/20">
              {error}
            </div>
          )}

          <div className="space-y-3 py-3 text-xs">
            <div>
              <label className="text-muted-foreground block mb-1">Project Name *</label>
              <Input
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="e.g. Real-Time Outbox Engine"
                autoFocus
                className="h-8 text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-muted-foreground block mb-1">
                  Project Key * <span className="text-[10px] text-muted-foreground">(2-10 chars)</span>
                </label>
                <Input
                  value={key}
                  onChange={(e) => setKey(e.target.value.toUpperCase())}
                  placeholder="e.g. NEX"
                  maxLength={10}
                  className="h-8 text-xs font-mono uppercase"
                />
              </div>

              <div>
                <label className="text-muted-foreground block mb-1">Project Lead</label>
                <select
                  value={leadId}
                  onChange={(e) => setLeadId(e.target.value)}
                  className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">No Lead Assigned</option>
                  {members.map((m) => (
                    <option key={m.user.id} value={m.user.id}>
                      {m.user.full_name || m.user.email}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-muted-foreground block mb-1">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of objectives and scope..."
                rows={2}
                className="w-full rounded-md border border-input bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            </div>

            {/* Visibility Toggle */}
            <div className="rounded-lg border border-border/60 p-3 bg-muted/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isPrivate ? (
                    <Lock className="h-4 w-4 text-amber-400" />
                  ) : (
                    <Globe className="h-4 w-4 text-primary" />
                  )}
                  <div>
                    <span className="font-semibold text-xs text-foreground block">
                      {isPrivate ? "Private Project" : "Public Project"}
                    </span>
                    <span className="text-[11px] text-muted-foreground block">
                      {isPrivate
                        ? "Only workspace admins and explicit members can view"
                        : "Visible to all members of this workspace"}
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={isPrivate}
                  onChange={(e) => setIsPrivate(e.target.checked)}
                  className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                />
              </div>
            </div>
          </div>

          <DialogFooter className="border-t border-border/40 pt-3">
            <Button type="button" variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting} className="text-xs h-8">
              {isSubmitting ? "Creating..." : "Create Project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

interface ProjectMembersDialogProps {
  project: Project | null
  workspaceId: string
  isOpen: boolean
  onClose: () => void
}

export const ProjectMembersDialog: React.FC<ProjectMembersDialogProps> = ({
  project,
  workspaceId,
  isOpen,
  onClose,
}) => {
  if (!project) return null

  const [members, setMembers] = useState<any[]>([])
  const [workspaceMembers, setWorkspaceMembers] = useState<WorkspaceMemberItem[]>([])
  const [selectedUserId, setSelectedUserId] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [projMembersRes, wsMembersRes] = await Promise.all([
        apiClient.request<any[]>(`/projects/${project.id}/members`),
        apiClient.request<WorkspaceMemberItem[]>(`/workspaces/${workspaceId}/members`),
      ])
      if (projMembersRes.success && projMembersRes.data) {
        setMembers(projMembersRes.data)
      }
      if (wsMembersRes.success && wsMembersRes.data) {
        setWorkspaceMembers(wsMembersRes.data)
      }
    } catch (err: any) {
      setError(err.message || "Failed to load project members")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen, project.id])

  const handleAddMember = async () => {
    if (!selectedUserId) return
    setError(null)
    try {
      const res = await apiClient.request(`/projects/${project.id}/members`, {
        method: "POST",
        body: JSON.stringify({ user_id: selectedUserId }),
      })
      if (!res.success) {
        throw new Error(res.error?.message || "Failed to add member")
      }
      setSelectedUserId("")
      await loadData()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleRemoveMember = async (userId: string) => {
    setError(null)
    try {
      const res = await apiClient.request(`/projects/${project.id}/members/${userId}`, {
        method: "DELETE",
      })
      if (!res.success) {
        throw new Error(res.error?.message || "Failed to remove member")
      }
      await loadData()
    } catch (err: any) {
      setError(err.message)
    }
  }

  // Workspace members not yet in project
  const eligibleMembers = workspaceMembers.filter(
    (wm) => !members.some((pm) => pm.user_id === wm.user.id)
  )

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border/80">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-amber-400" />
            <DialogTitle className="text-base font-semibold">
              Manage Members: {project.name}
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            This is a private project. Only members listed below or workspace admins have access.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-md bg-destructive/15 p-2 text-xs text-destructive border border-destructive/20">
            {error}
          </div>
        )}

        {/* Add Member Bar */}
        <div className="flex items-center gap-2 pt-2">
          <select
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
            className="flex-1 h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">Select a workspace member...</option>
            {eligibleMembers.map((em) => (
              <option key={em.user.id} value={em.user.id}>
                {em.user.full_name || em.user.email} ({em.role})
              </option>
            ))}
          </select>
          <Button
            size="sm"
            onClick={handleAddMember}
            disabled={!selectedUserId}
            className="h-8 text-xs shrink-0"
          >
            <UserPlus className="h-3.5 w-3.5 mr-1" />
            Add
          </Button>
        </div>

        {/* Members List */}
        <div className="space-y-2 py-3 max-h-60 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center text-xs text-muted-foreground">Loading members...</div>
          ) : members.length === 0 ? (
            <div className="p-4 text-center text-xs text-muted-foreground">
              No explicit members assigned yet.
            </div>
          ) : (
            members.map((m) => (
              <div
                key={m.id || m.user_id}
                className="flex items-center justify-between p-2 rounded-md border border-border/50 bg-muted/10 text-xs"
              >
                <div className="flex items-center gap-2">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="text-[10px]">
                      {(m.user?.full_name || m.user?.email || "U").slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <span className="font-medium text-foreground block">
                      {m.user?.full_name || m.user?.email}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{m.user?.email}</span>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-destructive"
                  onClick={() => handleRemoveMember(m.user_id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))
          )}
        </div>

        <DialogFooter className="border-t border-border/40 pt-3">
          <Button variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
