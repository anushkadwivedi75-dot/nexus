import { useEffect, useState } from "react"
import {
  UserPlus,
  Shield,
  Mail,
  MoreVertical,
  Trash2,
  Crown,
  Copy,
  Check,
  Clock,
  Ban,
  Loader2,
  AlertCircle,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { useAuthStore } from "@/stores/auth-store"
import { apiClient } from "@/services/api"
import type { WorkspaceInvitationItem, WorkspaceMemberItem } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function MembersPage() {
  const { currentWorkspace, transferOwnership, fetchWorkspaces } = useWorkspaceStore()
  const { user: currentUser } = useAuthStore()

  const [members, setMembers] = useState<WorkspaceMemberItem[]>([])
  const [invitations, setInvitations] = useState<WorkspaceInvitationItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Invite Modal
  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState<"member" | "admin">("member")
  const [isInviting, setIsInviting] = useState(false)
  const [inviteResult, setInviteResult] = useState<{ rawToken: string; url: string } | null>(null)
  const [copied, setCopied] = useState(false)

  // Transfer Ownership Modal
  const [isTransferOpen, setIsTransferOpen] = useState(false)
  const [selectedNewOwner, setSelectedNewOwner] = useState<string>("")
  const [isTransferring, setIsTransferring] = useState(false)

  const isOwner = currentWorkspace.role === "owner"
  const isAdmin = currentWorkspace.role === "admin" || isOwner

  const loadData = async () => {
    if (!currentWorkspace?.id) return
    setIsLoading(true)
    setError(null)
    try {
      const memRes = await apiClient.get(`/workspaces/${currentWorkspace.id}/members`)
      setMembers(memRes.data || [])

      if (isAdmin) {
        try {
          const invRes = await apiClient.get(`/workspaces/${currentWorkspace.id}/invitations`)
          setInvitations(invRes.data || [])
        } catch {
          // Member may not have admin rights to list invitations
        }
      }
    } catch (err: any) {
      setError(err.data?.detail || err.message || "Failed to load members.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [currentWorkspace?.id])

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inviteEmail.trim()) return

    setIsInviting(true)
    setError(null)
    try {
      const res = await apiClient.post(`/workspaces/${currentWorkspace.id}/invitations`, {
        email: inviteEmail.trim(),
        role: inviteRole,
      })
      const token = res.data?.raw_token
      setInviteResult({
        rawToken: token,
        url: `${window.location.origin}/invite/${token}`,
      })
      setInviteEmail("")
      loadData()
    } catch (err: any) {
      setError(err.data?.detail || err.message || "Failed to send invitation.")
    } finally {
      setIsInviting(false)
    }
  }

  const handleRevokeInvite = async (invitationId: string) => {
    try {
      await apiClient.post(`/workspaces/${currentWorkspace.id}/invitations/${invitationId}/revoke`)
      loadData()
    } catch (err: any) {
      setError(err.data?.detail || err.message || "Failed to revoke invitation.")
    }
  }

  const handleUpdateRole = async (targetUserId: string, newRole: "admin" | "member") => {
    try {
      await apiClient.patch(`/workspaces/${currentWorkspace.id}/members/${targetUserId}`, {
        role: newRole,
      })
      loadData()
    } catch (err: any) {
      setError(err.data?.detail || err.message || "Failed to update member role.")
    }
  }

  const handleRemoveMember = async (targetUserId: string) => {
    try {
      await apiClient.delete(`/workspaces/${currentWorkspace.id}/members/${targetUserId}`)
      loadData()
      fetchWorkspaces()
    } catch (err: any) {
      setError(err.data?.detail || err.message || "Failed to remove member.")
    }
  }

  const handleTransferOwnership = async () => {
    if (!selectedNewOwner) return
    setIsTransferring(true)
    setError(null)
    try {
      await transferOwnership(currentWorkspace.id, selectedNewOwner)
      setIsTransferOpen(false)
      loadData()
    } catch (err: any) {
      setError(err.data?.detail || err.message || "Failed to transfer ownership.")
    } finally {
      setIsTransferring(false)
    }
  }

  const copyInviteLink = () => {
    if (inviteResult?.url) {
      navigator.clipboard.writeText(inviteResult.url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Workspace Members
          </h1>
          <p className="text-xs text-muted-foreground">
            Manage contributors, access permissions, and roles for {currentWorkspace.name}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isOwner && members.length > 1 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsTransferOpen(true)}
              className="text-xs border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
            >
              <Crown className="h-3.5 w-3.5 mr-1.5" />
              Transfer Ownership
            </Button>
          )}

          {isAdmin && (
            <Button
              size="sm"
              onClick={() => {
                setInviteResult(null)
                setIsInviteOpen(true)
              }}
              className="text-xs bg-violet-600 hover:bg-violet-500"
            >
              <UserPlus className="h-3.5 w-3.5 mr-1.5" />
              Invite Member
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active Members List */}
      <div className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
          Active Members ({members.length})
        </h2>

        {isLoading ? (
          <div className="p-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
            <span>Loading members...</span>
          </div>
        ) : (
          members.map((m) => {
            const isCaller = m.user_id === currentUser?.id
            const canManage =
              (isOwner && m.role !== "owner") ||
              (isAdmin && m.role === "member") ||
              isCaller

            const initials =
              m.user.full_name
                .split(" ")
                .map((p) => p[0])
                .join("")
                .toUpperCase()
                .slice(0, 2) || "U"

            return (
              <Card key={m.id} className="border-border/60 bg-card/50 hover:bg-card/70 transition-colors">
                <CardContent className="p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-primary/20 text-primary text-xs font-bold">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                        {m.user.full_name}
                        {isCaller && (
                          <span className="text-[10px] text-muted-foreground font-normal">(you)</span>
                        )}
                      </span>
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Mail className="h-3 w-3" /> {m.user.email}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge
                      variant={m.role === "owner" ? "default" : m.role === "admin" ? "purple" : "secondary"}
                      className="text-[10px] capitalize"
                    >
                      {m.role === "owner" && <Crown className="h-2.5 w-2.5 mr-1 text-amber-300" />}
                      {m.role === "admin" && <Shield className="h-2.5 w-2.5 mr-1" />}
                      {m.role}
                    </Badge>

                    {canManage && m.role !== "owner" && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon-sm" className="h-7 w-7">
                            <MoreVertical className="h-3.5 w-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-40 text-xs">
                          {isAdmin && !isCaller && (
                            <>
                              {m.role === "member" && (
                                <DropdownMenuItem onClick={() => handleUpdateRole(m.user_id, "admin")}>
                                  Promote to Admin
                                </DropdownMenuItem>
                              )}
                              {m.role === "admin" && isOwner && (
                                <DropdownMenuItem onClick={() => handleUpdateRole(m.user_id, "member")}>
                                  Demote to Member
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                            </>
                          )}
                          <DropdownMenuItem
                            onClick={() => handleRemoveMember(m.user_id)}
                            className="text-rose-400 focus:text-rose-400 cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                            {isCaller ? "Leave Workspace" : "Remove Member"}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })
        )}
      </div>

      {/* Pending Invitations */}
      {isAdmin && invitations.length > 0 && (
        <div className="space-y-2 pt-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
            Pending Invitations ({invitations.length})
          </h2>
          <div className="space-y-2">
            {invitations.map((inv) => (
              <Card key={inv.id} className="border-border/40 bg-card/30">
                <CardContent className="p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                      <Clock className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-foreground font-medium">{inv.email}</span>
                      <span className="text-[10px] text-muted-foreground">
                        Invited as <strong className="capitalize">{inv.role}</strong>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRevokeInvite(inv.id)}
                      className="text-xs h-7 text-muted-foreground hover:text-rose-400"
                    >
                      <Ban className="w-3.5 h-3.5 mr-1" />
                      Revoke
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Invite Modal */}
      <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Invite a team member</DialogTitle>
            <DialogDescription>
              Generate a cryptographic invite link for joining {currentWorkspace.name}.
            </DialogDescription>
          </DialogHeader>

          {inviteResult ? (
            <div className="space-y-4 py-3">
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
                Invitation created successfully! Share this private link with the invitee:
              </div>
              <div className="flex items-center gap-2">
                <Input readOnly value={inviteResult.url} className="text-xs font-mono select-all" />
                <Button size="sm" onClick={copyInviteLink} className="shrink-0">
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
              <DialogFooter>
                <Button size="sm" onClick={() => setIsInviteOpen(false)}>
                  Done
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <form onSubmit={handleCreateInvite} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Email Address</label>
                <Input
                  type="email"
                  placeholder="teammate@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  autoFocus
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as "member" | "admin")}
                  className="w-full h-8 px-2.5 rounded-md border border-input bg-card/60 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="member">Member — Can participate in projects and tasks</option>
                  <option value="admin">Admin — Can manage members, projects, and settings</option>
                </select>
              </div>

              <DialogFooter className="pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsInviteOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={isInviting || !inviteEmail.trim()}>
                  {isInviting ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : null}
                  Generate Invite
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Transfer Ownership Modal */}
      <Dialog open={isTransferOpen} onOpenChange={setIsTransferOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <div className="flex items-center gap-2 text-amber-400 mb-1">
              <Crown className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Transfer Ownership</span>
            </div>
            <DialogTitle>Transfer workspace ownership</DialogTitle>
            <DialogDescription>
              Select an active member to receive ownership. You will be demoted to an <strong>Administrator</strong>.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">New Owner</label>
              <select
                value={selectedNewOwner}
                onChange={(e) => setSelectedNewOwner(e.target.value)}
                className="w-full h-8 px-2.5 rounded-md border border-input bg-card/60 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
              >
                <option value="">Select a member...</option>
                {members
                  .filter((m) => m.user_id !== currentUser?.id)
                  .map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.user.full_name} ({m.user.email})
                    </option>
                  ))}
              </select>
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px]">
              ⚠️ This action is irreversible unless the new owner transfers ownership back to you.
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsTransferOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={isTransferring || !selectedNewOwner}
                onClick={handleTransferOwnership}
              >
                {isTransferring ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : null}
                Confirm Transfer
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
