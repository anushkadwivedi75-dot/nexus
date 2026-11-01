import * as React from "react"
import {
  TrendingUp,
  FolderKanban,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  Plus,
  Sparkles,
  Filter,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { mockStats, mockProjects, mockActivities } from "@/data/mock-data"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function OverviewPage() {
  const { currentWorkspace, setCommandPaletteOpen } = useWorkspaceStore()
  const [filter, setFilter] = React.useState<"all" | "active" | "planning">("all")

  const filteredProjects = mockProjects.filter((p) => {
    if (filter === "all") return true
    return p.status === filter
  })

  return (
    <div className="space-y-6">
      {/* 1. Page Header & Actions */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {currentWorkspace.name}
            </h1>
            <Badge variant="purple" className="text-[10px]">
              {currentWorkspace.plan}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Sprint cycle 26.4 &bull; 4 active projects &bull; 18 team contributors
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCommandPaletteOpen(true)}
            className="text-xs"
          >
            <Filter className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
            Filter Views
          </Button>

          <Button
            size="sm"
            onClick={() => setCommandPaletteOpen(true)}
            className="text-xs shadow-sm shadow-primary/25"
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            Create Issue
          </Button>
        </div>
      </div>

      {/* 2. Key Metrics Grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {mockStats.map((stat, i) => {
          const icons = [TrendingUp, FolderKanban, CheckCircle2, Clock]
          const Icon = icons[i % icons.length]

          return (
            <Card key={stat.label} className="border-border/60 bg-card/70 hover:border-border transition-all">
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">{stat.label}</span>
                  <div className="flex h-6 w-6 items-center justify-center rounded bg-muted/60 text-muted-foreground">
                    <Icon className="h-3.5 w-3.5 text-primary" />
                  </div>
                </div>

                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold tracking-tight text-foreground font-mono">
                    {stat.value}
                  </span>
                  <Badge
                    variant={stat.isPositive ? "success" : "secondary"}
                    className="text-[10px] px-1.5 py-0 font-mono"
                  >
                    {stat.change}
                  </Badge>
                </div>

                <p className="text-[11px] text-muted-foreground/80 truncate">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* 3. Core Content: Projects & Activity Feed */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column: Projects Roadmap (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground tracking-tight">
                Active Projects
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Roadmap milestones and progress distribution
              </p>
            </div>

            <Tabs
              value={filter}
              onValueChange={(v) => setFilter(v as any)}
              className="w-auto"
            >
              <TabsList className="h-7 text-xs">
                <TabsTrigger value="all" className="text-[11px] px-2 py-0.5">All</TabsTrigger>
                <TabsTrigger value="active" className="text-[11px] px-2 py-0.5">Active</TabsTrigger>
                <TabsTrigger value="planning" className="text-[11px] px-2 py-0.5">Planning</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {filteredProjects.map((prj) => {
              const progressPct = Math.round((prj.tasksCompleted / prj.tasksTotal) * 100)

              return (
                <Card
                  key={prj.id}
                  className="group relative border-border/70 bg-card/60 hover:bg-card/90 hover:border-border transition-all cursor-pointer"
                  onClick={() => setCommandPaletteOpen(true)}
                >
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-2 rounded-full shrink-0"
                          style={{ backgroundColor: prj.colorHex }}
                        />
                        <span className="font-mono text-[11px] text-muted-foreground font-semibold">
                          {prj.key}
                        </span>
                      </div>

                      <Badge
                        variant={prj.status === "active" ? "default" : "secondary"}
                        className="text-[9px] px-1.5 py-0 capitalize"
                      >
                        {prj.status}
                      </Badge>
                    </div>

                    <div className="space-y-1">
                      <h3 className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors flex items-center justify-between">
                        <span>{prj.name}</span>
                        <ArrowUpRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-primary" />
                      </h3>
                      <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                        {prj.description}
                      </p>
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-1 pt-1">
                      <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                        <span>Progress</span>
                        <span>{prj.tasksCompleted}/{prj.tasksTotal} ({progressPct}%)</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/60">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${progressPct}%`,
                            backgroundColor: prj.colorHex,
                          }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-muted-foreground/80 pt-1 border-t border-border/40">
                      <span>Lead: {prj.leadName}</span>
                      <span>Updated {prj.updatedAt}</span>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Useful Empty State Design Pattern Preview */}
          <Card className="border-dashed border-border/80 bg-card/20 p-4 text-center">
            <div className="flex flex-col items-center justify-center space-y-2 py-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted/60 text-muted-foreground">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <h4 className="text-xs font-semibold text-foreground">
                Sprint Retrospective Ready
              </h4>
              <p className="text-[11px] text-muted-foreground max-w-sm">
                Sprint 26.3 concluded with 100% committed deliverables completed. No pending blockers require action.
              </p>
              <Button
                variant="subtle"
                size="sm"
                className="text-xs h-7 mt-2"
                onClick={() => setCommandPaletteOpen(true)}
              >
                Create Next Sprint Goal
              </Button>
            </div>
          </Card>
        </div>

        {/* Right Column: Live Activity Feed (1 col) */}
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground tracking-tight">
              Activity Stream
            </h2>
            <p className="text-[11px] text-muted-foreground">
              Real-time collaboration across this workspace
            </p>
          </div>

          <Card className="border-border/70 bg-card/60">
            <CardContent className="p-3 divide-y divide-border/40">
              {mockActivities.map((act) => (
                <div key={act.id} className="py-2.5 first:pt-1 last:pb-1 flex items-start gap-2.5">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-[10px] font-bold mt-0.5">
                    {act.actorName.split(" ").map((n) => n[0]).join("")}
                  </div>

                  <div className="flex flex-col min-w-0 space-y-0.5">
                    <p className="text-xs text-foreground leading-snug">
                      <strong className="font-medium">{act.actorName}</strong>{" "}
                      <span className="text-muted-foreground">{act.action}</span>
                    </p>

                    <div className="flex items-center gap-1.5">
                      {act.targetKey && (
                        <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5 font-mono">
                          {act.targetKey}
                        </Badge>
                      )}
                      <span className="text-[11px] text-foreground/80 truncate">
                        {act.targetTitle}
                      </span>
                    </div>

                    <span className="text-[10px] text-muted-foreground/70">
                      {act.timestamp}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Quick Shortcuts Hint Card */}
          <Card className="border-border/50 bg-sidebar/50 p-3">
            <div className="space-y-2">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Keyboard Shortcuts
              </span>
              <div className="space-y-1 text-xs">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Command palette</span>
                  <kbd className="font-mono text-[10px] bg-muted/60 px-1 py-0.5 rounded border border-border/50">Cmd + K</kbd>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Toggle sidebar</span>
                  <kbd className="font-mono text-[10px] bg-muted/60 px-1 py-0.5 rounded border border-border/50">Cmd + \</kbd>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Quick task creation</span>
                  <kbd className="font-mono text-[10px] bg-muted/60 px-1 py-0.5 rounded border border-border/50">C</kbd>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
