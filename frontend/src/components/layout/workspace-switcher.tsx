import * as React from "react"
import { Check, ChevronsUpDown, Plus, Sparkles, Building2 } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export function WorkspaceSwitcher({ isCollapsed = false }: { isCollapsed?: boolean }) {
  const { workspaces, currentWorkspace, setWorkspace, createWorkspace, fetchWorkspaces } =
    useWorkspaceStore()
  const [isCreateOpen, setIsCreateOpen] = React.useState(false)
  const [newWsName, setNewWsName] = React.useState("")
  const [newWsSlug, setNewWsSlug] = React.useState("")
  const [createError, setCreateError] = React.useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  React.useEffect(() => {
    fetchWorkspaces()
  }, [fetchWorkspaces])

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWsName.trim()) return
    const slug = (newWsSlug.trim() || newWsName.toLowerCase().replace(/\s+/g, "-")).replace(/[^a-z0-9-]/g, "")
    
    setIsSubmitting(true)
    setCreateError(null)
    try {
      await createWorkspace(newWsName.trim(), slug)
      setNewWsName("")
      setNewWsSlug("")
      setIsCreateOpen(false)
    } catch (err: any) {
      setCreateError(err.data?.detail || err.message || "Failed to create workspace.")
    } finally {
      setIsSubmitting(false)
    }
  }

  // Trigger Button
  const triggerButton = (
    <button
      className={cn(
        "flex w-full items-center gap-2 rounded-md border border-sidebar-border bg-sidebar-accent/50 p-1.5 text-left text-xs transition-colors hover:bg-sidebar-accent hover:border-sidebar-border/80 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring select-none",
        isCollapsed ? "justify-center px-1" : "justify-between"
      )}
      aria-label="Switch workspace"
    >
      <div className="flex items-center gap-2 overflow-hidden">
        <div
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-[11px] font-bold text-white shadow-sm"
          style={{ backgroundColor: currentWorkspace.colorHex }}
        >
          {currentWorkspace.initials}
        </div>
        {!isCollapsed && (
          <div className="flex flex-col min-w-0">
            <span className="truncate font-medium text-foreground tracking-tight text-xs">
              {currentWorkspace.name}
            </span>
            <span className="text-[10px] text-muted-foreground capitalize">
              {currentWorkspace.plan} Plan
            </span>
          </div>
        )}
      </div>
      {!isCollapsed && (
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground/80" />
      )}
    </button>
  )

  return (
    <>
      <DropdownMenu>
        {isCollapsed ? (
          <TooltipProvider delayDuration={150}>
            <Tooltip>
              <TooltipTrigger asChild>
                <DropdownMenuTrigger asChild>
                  {triggerButton}
                </DropdownMenuTrigger>
              </TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                {currentWorkspace.name} ({currentWorkspace.plan})
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : (
          <DropdownMenuTrigger asChild>
            {triggerButton}
          </DropdownMenuTrigger>
        )}

        <DropdownMenuContent
          className="w-64 p-1.5"
          align="start"
          sideOffset={6}
        >
          <DropdownMenuLabel className="flex items-center justify-between text-[10px] text-muted-foreground font-semibold px-2 py-1">
            <span>Workspaces</span>
            <span className="text-[9px] text-muted-foreground/70 font-normal">
              {workspaces.length} active
            </span>
          </DropdownMenuLabel>

          <DropdownMenuSeparator />

          <div className="space-y-0.5">
            {workspaces.map((ws) => {
              const isSelected = ws.id === currentWorkspace.id
              return (
                <DropdownMenuItem
                  key={ws.id}
                  onClick={() => setWorkspace(ws.id)}
                  className={cn(
                    "flex items-center justify-between px-2 py-1.5 cursor-pointer rounded text-xs",
                    isSelected ? "bg-accent text-accent-foreground font-medium" : "hover:bg-accent/60"
                  )}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <div
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-bold text-white"
                      style={{ backgroundColor: ws.colorHex }}
                    >
                      {ws.initials}
                    </div>
                    <div className="flex flex-col truncate">
                      <span className="truncate text-xs">{ws.name}</span>
                      <span className="text-[10px] text-muted-foreground lowercase">
                        {ws.slug}.nexus.io
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Badge variant="secondary" className="text-[9px] px-1 py-0 h-4">
                      {ws.role}
                    </Badge>
                    {isSelected && (
                      <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                    )}
                  </div>
                </DropdownMenuItem>
              )
            })}
          </div>

          <DropdownMenuSeparator />

          <DropdownMenuItem
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 px-2 py-1.5 text-xs text-primary hover:text-primary hover:bg-primary/10 rounded cursor-pointer transition-colors"
          >
            <div className="flex h-5 w-5 items-center justify-center rounded border border-dashed border-primary/40 bg-primary/5">
              <Plus className="h-3 w-3 text-primary" />
            </div>
            <span className="font-medium">Create workspace</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Mock Create Workspace Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <div className="flex items-center gap-2 text-primary mb-1">
              <Building2 className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">New Workspace</span>
            </div>
            <DialogTitle>Create a workspace</DialogTitle>
            <DialogDescription>
              Workspaces are isolated multi-tenant containers for your team projects, boards, and members.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateSubmit} className="space-y-4 py-2">
            {createError && (
              <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                {createError}
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Workspace Name</label>
              <Input
                placeholder="e.g. Acme Studio, Nexus Labs"
                value={newWsName}
                onChange={(e) => {
                  setNewWsName(e.target.value)
                  if (!newWsSlug || newWsSlug === newWsName.toLowerCase().replace(/\s+/g, "-")) {
                    setNewWsSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"))
                  }
                }}
                autoFocus
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">URL Slug</label>
              <div className="flex items-center gap-1 rounded-md border border-input bg-card/40 px-2.5 py-1 text-xs text-muted-foreground">
                <span className="text-muted-foreground/70">nexus.io/</span>
                <input
                  type="text"
                  className="w-full bg-transparent text-foreground outline-none text-xs"
                  placeholder="acme-studio"
                  value={newWsSlug}
                  onChange={(e) => setNewWsSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                />
              </div>
            </div>

            <div className="rounded-md bg-muted/40 p-2.5 border border-border/50 text-[11px] text-muted-foreground flex items-start gap-2">
              <Sparkles className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
              <span>
                You will be assigned as the exclusive <strong>Workspace Owner</strong> with full administrative authority.
              </span>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={!newWsName.trim() || isSubmitting}>
                {isSubmitting ? "Creating..." : "Create Workspace"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

