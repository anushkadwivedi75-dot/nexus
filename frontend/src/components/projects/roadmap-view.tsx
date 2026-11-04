import React, { useEffect } from "react"
import { Calendar, CheckCircle2, Clock } from "lucide-react"
import { useProjectStore } from "@/stores/project-store"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

interface RoadmapViewProps {
  projectId: string
  projectKey: string
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({ projectId, projectKey }) => {
  const { roadmap, isLoadingRoadmap, fetchRoadmap } = useProjectStore()

  useEffect(() => {
    fetchRoadmap(projectId)
  }, [projectId])

  if (isLoadingRoadmap) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-primary" />
      </div>
    )
  }

  if (roadmap.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 p-12 text-center">
        <Calendar className="mx-auto h-8 w-8 text-muted-foreground/50 mb-3" />
        <h4 className="text-sm font-semibold text-foreground mb-1">No Roadmap Milestones Yet</h4>
        <p className="text-xs text-muted-foreground max-w-sm mx-auto">
          Tasks with a set due date automatically appear here on the project roadmap schedule.
        </p>
      </div>
    )
  }

  const completedCount = roadmap.filter((m) => m.is_completed).length
  const pctCompleted = Math.round((completedCount / roadmap.length) * 100)

  return (
    <div className="space-y-6">
      {/* Roadmap Summary Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="bg-card/40 border-border/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-[11px] text-muted-foreground block">Milestones</span>
              <span className="text-xl font-bold text-foreground">{roadmap.length}</span>
            </div>
            <Clock className="h-5 w-5 text-primary" />
          </CardContent>
        </Card>

        <Card className="bg-card/40 border-border/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-[11px] text-muted-foreground block">Completed</span>
              <span className="text-xl font-bold text-emerald-400">{completedCount}</span>
            </div>
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          </CardContent>
        </Card>

        <Card className="bg-card/40 border-border/60">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <span className="text-[11px] text-muted-foreground block">Progress</span>
              <span className="text-xl font-bold text-foreground">{pctCompleted}%</span>
            </div>
            <div className="w-12 h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all"
                style={{ width: `${pctCompleted}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chronological Milestone Timeline */}
      <div className="relative border-l border-border/60 ml-4 pl-6 space-y-6">
        {roadmap.map((milestone) => {
          const dateObj = new Date(milestone.due_date)
          const isOverdue = !milestone.is_completed && dateObj.getTime() < Date.now()

          return (
            <div key={milestone.id} className="relative group">
              {/* Dot */}
              <div
                className={`absolute -left-[31px] top-1.5 h-3.5 w-3.5 rounded-full border-2 border-background transition-transform group-hover:scale-125 ${
                  milestone.is_completed
                    ? "bg-emerald-500"
                    : isOverdue
                    ? "bg-red-500"
                    : "bg-primary"
                }`}
              />

              <div className="rounded-lg border border-border/70 bg-card/60 p-3.5 hover:border-border transition-all">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-muted-foreground">
                      {projectKey}-{milestone.task_number}
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {milestone.title}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 border capitalize"
                      style={{
                        borderColor: `${milestone.status_color}40`,
                        color: milestone.status_color,
                        backgroundColor: `${milestone.status_color}15`,
                      }}
                    >
                      {milestone.status_name}
                    </Badge>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 capitalize">
                      {milestone.priority}
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <Calendar className="h-3 w-3" />
                  <span>
                    Due {dateObj.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" })}
                  </span>
                  {isOverdue && (
                    <span className="text-red-400 font-medium ml-2">Overdue</span>
                  )}
                  {milestone.is_completed && (
                    <span className="text-emerald-400 font-medium ml-2">Completed</span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
