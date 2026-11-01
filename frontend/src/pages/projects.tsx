import { Plus, Search, Users } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { mockProjects } from "@/data/mock-data"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"

export function ProjectsPage() {
  const { currentWorkspace, setCommandPaletteOpen } = useWorkspaceStore()

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Projects Roadmap
          </h1>
          <p className="text-xs text-muted-foreground">
            Manage projects, milestone tracking, and task status columns for {currentWorkspace.name}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setCommandPaletteOpen(true)}
            className="text-xs"
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Project
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input placeholder="Filter projects by key or name..." className="pl-8" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {mockProjects.map((prj) => {
          const progressPct = Math.round((prj.tasksCompleted / prj.tasksTotal) * 100)

          return (
            <Card key={prj.id} className="border-border/70 bg-card/60 hover:border-border transition-all">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: prj.colorHex }}
                    />
                    <span className="font-mono text-xs text-muted-foreground font-semibold">
                      {prj.key}
                    </span>
                    <span className="font-semibold text-xs text-foreground">
                      {prj.name}
                    </span>
                  </div>

                  <Badge variant={prj.status === "active" ? "default" : "secondary"} className="text-[9px] capitalize">
                    {prj.status}
                  </Badge>
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  {prj.description}
                </p>

                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                    <span>Task Completion</span>
                    <span>{prj.tasksCompleted} / {prj.tasksTotal} ({progressPct}%)</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted/60 overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${progressPct}%`, backgroundColor: prj.colorHex }}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/40">
                  <div className="flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5" />
                    <span>Lead: {prj.leadName}</span>
                  </div>
                  <span>Updated {prj.updatedAt}</span>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
