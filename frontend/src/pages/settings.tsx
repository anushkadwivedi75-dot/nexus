import { Shield, Database, Lock } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

export function SettingsPage() {
  const { currentWorkspace } = useWorkspaceStore()

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
        <Card className="border-border/60 bg-card/60">
          <CardHeader className="p-4 pb-2">
            <CardTitle>General Information</CardTitle>
            <CardDescription>Primary workspace identification and vanity URL routing</CardDescription>
          </CardHeader>
          <CardContent className="p-4 space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Workspace Name</label>
              <Input defaultValue={currentWorkspace.name} />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Workspace Slug</label>
              <div className="flex items-center gap-1 rounded-md border border-input bg-card/40 px-2.5 py-1 text-xs text-muted-foreground">
                <span>nexus.io/</span>
                <input
                  type="text"
                  className="w-full bg-transparent text-foreground outline-none text-xs font-mono"
                  defaultValue={currentWorkspace.slug}
                />
              </div>
            </div>

            <Button size="sm" className="text-xs mt-2">
              Save Changes (Mock)
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/60">
          <CardHeader className="p-4 pb-2">
            <CardTitle>Security & Tenancy Invariant</CardTitle>
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
      </div>
    </div>
  )
}
