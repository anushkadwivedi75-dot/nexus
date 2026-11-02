import { useState, useEffect } from "react"
import { Shield, Database, Lock, AlertTriangle, Loader2, Check } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export function SettingsPage() {
  const { currentWorkspace, updateWorkspace, deleteWorkspace } = useWorkspaceStore()

  const [name, setName] = useState(currentWorkspace?.name || "")
  const [slug, setSlug] = useState(currentWorkspace?.slug || "")
  const [isUpdating, setIsUpdating] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Delete Modal
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState("")
  const [isDeleting, setIsDeleting] = useState(false)

  const isOwner = currentWorkspace?.role === "owner"
  const isAdmin = currentWorkspace?.role === "admin" || isOwner

  useEffect(() => {
    if (currentWorkspace) {
      setName(currentWorkspace.name)
      setSlug(currentWorkspace.slug)
    }
  }, [currentWorkspace?.id])

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !slug.trim()) return

    setIsUpdating(true)
    setErrorMessage(null)
    setSaveSuccess(false)
    try {
      await updateWorkspace(currentWorkspace.id, {
        name: name.trim(),
        slug: slug.trim().toLowerCase(),
      })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch (err: any) {
      setErrorMessage(err.data?.detail || err.message || "Failed to update workspace.")
    } finally {
      setIsUpdating(false)
    }
  }

  const handleDelete = async () => {
    if (deleteConfirmText !== currentWorkspace.name) return

    setIsDeleting(true)
    setErrorMessage(null)
    try {
      await deleteWorkspace(currentWorkspace.id)
      setIsDeleteOpen(false)
    } catch (err: any) {
      setErrorMessage(err.data?.detail || err.message || "Failed to delete workspace.")
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="border-b border-border/50 pb-5">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          Workspace Settings
        </h1>
        <p className="text-xs text-muted-foreground">
          Configuration, vanity slugs, and security invariants for {currentWorkspace.name}
        </p>
      </div>

      <div className="space-y-4 max-w-2xl">
        {errorMessage && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {errorMessage}
          </div>
        )}

        {saveSuccess && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <Check className="w-4 h-4" />
            <span>Workspace settings saved successfully!</span>
          </div>
        )}

        <Card className="border-border/60 bg-card/60">
          <CardHeader className="p-4 pb-2">
            <CardTitle>General Information</CardTitle>
            <CardDescription>Primary workspace identification and vanity URL routing</CardDescription>
          </CardHeader>
          <CardContent className="p-4">
            <form onSubmit={handleUpdate} className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Workspace Name</label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={!isAdmin || isUpdating}
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Workspace Slug</label>
                <div className="flex items-center gap-1 rounded-md border border-input bg-card/40 px-2.5 py-1 text-xs text-muted-foreground">
                  <span>nexus.io/</span>
                  <input
                    type="text"
                    className="w-full bg-transparent text-foreground outline-none text-xs font-mono disabled:opacity-50"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                    disabled={!isAdmin || isUpdating}
                    required
                  />
                </div>
              </div>

              {isAdmin && (
                <Button size="sm" type="submit" disabled={isUpdating} className="text-xs mt-2">
                  {isUpdating ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : null}
                  Save Changes
                </Button>
              )}
            </form>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60">
          <CardHeader className="p-4 pb-2">
            <CardTitle>Security & Tenancy Invariants</CardTitle>
            <CardDescription>PostgreSQL 16 composite isolation status</CardDescription>
          </CardHeader>
          <CardContent className="p-4 space-y-2.5 text-xs text-muted-foreground">
            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                <span className="font-medium text-foreground">Multi-Tenant Boundary</span>
              </div>
              <Badge variant="success" className="text-[10px]">Composite FK Enforced</Badge>
            </div>

            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-primary" />
                <span className="font-medium text-foreground">Single Owner Invariant</span>
              </div>
              <Badge variant="purple" className="text-[10px]">uq_workspace_single_owner</Badge>
            </div>

            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                <span className="font-medium text-foreground">Audit Log Immutability</span>
              </div>
              <Badge variant="secondary" className="text-[10px]">nexus_app (REVOKE DML)</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone: Delete Workspace */}
        {isOwner && (
          <Card className="border-rose-900/40 bg-rose-950/10">
            <CardHeader className="p-4 pb-2">
              <div className="flex items-center gap-2 text-rose-400">
                <AlertTriangle className="h-4 w-4" />
                <CardTitle className="text-rose-400">Danger Zone</CardTitle>
              </div>
              <CardDescription className="text-rose-400/70">
                Permanently delete this workspace and all associated projects, tasks, and data.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-2">
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  setDeleteConfirmText("")
                  setIsDeleteOpen(true)
                }}
                className="text-xs bg-rose-600 hover:bg-rose-500"
              >
                Delete Workspace
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <div className="flex items-center gap-2 text-rose-500 mb-1">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Delete Workspace</span>
            </div>
            <DialogTitle>Are you absolutely sure?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete <strong>{currentWorkspace.name}</strong>, all member associations, and all project data.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">
                Type <strong>{currentWorkspace.name}</strong> to confirm:
              </label>
              <Input
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder={currentWorkspace.name}
                autoFocus
              />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsDeleteOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={deleteConfirmText !== currentWorkspace.name || isDeleting}
                onClick={handleDelete}
              >
                {isDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : null}
                Permanently Delete
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
