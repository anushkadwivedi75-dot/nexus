import { CheckSquare, Plus, Filter, Calendar } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

const mockUserTasks = [
  {
    id: "task-1",
    key: "CORE-104",
    title: "Implement deterministic two-column status locks (ORDER BY id ASC)",
    project: "Real-Time Outbox Engine",
    priority: "urgent",
    status: "In Progress",
    dueDate: "Today",
  },
  {
    id: "task-2",
    key: "UI-15",
    title: "Build collapsible left sidebar with tooltips and active state pill",
    project: "Design System & Dark-First Shell",
    priority: "high",
    status: "In Review",
    dueDate: "Tomorrow",
  },
  {
    id: "task-3",
    key: "AUTH-89",
    title: "Verify crash-safe refresh grace-chain traversal on Redis miss",
    project: "Session Security & Rotation",
    priority: "medium",
    status: "Done",
    dueDate: "Oct 28",
  },
  {
    id: "task-4",
    key: "CORE-99",
    title: "Configure 64-bit atomic counter check constraint in PostgreSQL",
    project: "Real-Time Outbox Engine",
    priority: "low",
    status: "Backlog",
    dueDate: "Nov 4",
  },
]

export function TasksPage() {
  const { setCommandPaletteOpen } = useWorkspaceStore()

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            My Tasks
          </h1>
          <p className="text-xs text-muted-foreground">
            Tasks assigned to you across all active workspace projects
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setCommandPaletteOpen(true)}
            className="text-xs"
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Task
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-7 text-xs">
            <Filter className="h-3 w-3 mr-1" /> All Statuses
          </Button>
          <Button variant="outline" size="sm" className="h-7 text-xs">
            Priority: High & Urgent
          </Button>
        </div>
        <span className="text-xs text-muted-foreground">
          Showing 4 of 8 tasks
        </span>
      </div>

      <div className="space-y-2">
        {mockUserTasks.map((t) => (
          <Card key={t.id} className="border-border/60 bg-card/50 hover:bg-card hover:border-border transition-colors">
            <CardContent className="p-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <CheckSquare className="h-4 w-4 text-muted-foreground hover:text-primary cursor-pointer shrink-0" />
                <Badge variant="secondary" className="font-mono text-[10px] px-1 py-0 h-4 shrink-0">
                  {t.key}
                </Badge>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-medium text-foreground truncate">
                    {t.title}
                  </span>
                  <span className="text-[10px] text-muted-foreground truncate">
                    {t.project}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <Badge
                  variant={
                    t.priority === "urgent"
                      ? "destructive"
                      : t.priority === "high"
                      ? "warning"
                      : "secondary"
                  }
                  className="text-[9px] px-1.5 py-0 capitalize"
                >
                  {t.priority}
                </Badge>

                <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Calendar className="h-3 w-3" />
                  <span>{t.dueDate}</span>
                </div>

                <Badge variant="outline" className="text-[10px] font-normal">
                  {t.status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

