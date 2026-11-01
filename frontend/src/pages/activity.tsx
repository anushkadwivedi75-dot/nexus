import { Clock } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { mockActivities } from "@/data/mock-data"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

export function ActivityPage() {
  const { currentWorkspace } = useWorkspaceStore()

  return (
    <div className="space-y-6">
      <div className="border-b border-border/50 pb-5">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          Workspace Activity
        </h1>
        <p className="text-xs text-muted-foreground">
          Comprehensive chronological timeline for {currentWorkspace.name}
        </p>
      </div>

      <Card className="border-border/60 bg-card/60">
        <CardContent className="p-4 divide-y divide-border/40">
          {mockActivities.map((act) => (
            <div key={act.id} className="py-3 first:pt-1 last:pb-1 flex items-start gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold mt-0.5">
                {act.actorName.split(" ").map((n) => n[0]).join("")}
              </div>

              <div className="flex flex-col min-w-0 space-y-1">
                <p className="text-xs text-foreground">
                  <strong className="font-semibold">{act.actorName}</strong>{" "}
                  <span className="text-muted-foreground">{act.action}</span>
                </p>

                <div className="flex items-center gap-2">
                  {act.targetKey && (
                    <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4 font-mono">
                      {act.targetKey}
                    </Badge>
                  )}
                  <span className="text-xs text-foreground/90 font-medium">
                    {act.targetTitle}
                  </span>
                </div>

                <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>{act.timestamp}</span>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
