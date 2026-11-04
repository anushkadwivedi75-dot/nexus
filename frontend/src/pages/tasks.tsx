import { useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  Lock,
  Globe,
  Layers,
  ArrowLeft,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { useProjectStore } from "@/stores/project-store"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { KanbanBoard } from "@/components/kanban/board"

export function TasksPage() {
  const { projectId } = useParams<{ projectId?: string }>()
  const navigate = useNavigate()
  const { currentWorkspace } = useWorkspaceStore()
  const {
    projects,
    activeProject,
    isLoadingProjects,
    fetchProjects,
    setActiveProject,
  } = useProjectStore()

  useEffect(() => {
    if (currentWorkspace?.id) {
      fetchProjects(currentWorkspace.id)
    }
  }, [currentWorkspace?.id])

  useEffect(() => {
    if (projects.length > 0) {
      if (projectId) {
        const match = projects.find((p) => p.id === projectId)
        if (match && match.id !== activeProject?.id) {
          setActiveProject(match)
        }
      } else if (!activeProject) {
        setActiveProject(projects[0])
      }
    }
  }, [projectId, projects])

  const handleProjectChange = (id: string) => {
    const selected = projects.find((p) => p.id === id)
    if (selected) {
      setActiveProject(selected)
      navigate(`/projects/${selected.id}`)
    }
  }

  if (isLoadingProjects && projects.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 p-12 text-center max-w-lg mx-auto mt-12">
        <Layers className="mx-auto h-8 w-8 text-muted-foreground/50 mb-3" />
        <h4 className="text-sm font-semibold text-foreground mb-1">No Projects Found</h4>
        <p className="text-xs text-muted-foreground mb-4">
          Create a project to access Kanban boards and workflow automation.
        </p>
        <Button size="sm" onClick={() => navigate("/projects")} className="text-xs">
          Go to Projects
        </Button>
      </div>
    )
  }

  const current = activeProject || projects[0]

  return (
    <div className="space-y-4">
      {/* Board Top Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            onClick={() => navigate("/projects")}
            title="Back to Projects"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                {current.key}
              </span>
              <h1 className="text-lg font-bold tracking-tight text-foreground">
                {current.name}
              </h1>
              {current.is_private ? (
                <Badge
                  variant="outline"
                  className="text-[10px] px-1.5 py-0 text-amber-400 border-amber-500/30 bg-amber-500/10 gap-1"
                >
                  <Lock className="h-2.5 w-2.5" />
                  Private
                </Badge>
              ) : (
                <Badge
                  variant="secondary"
                  className="text-[10px] px-1.5 py-0 text-muted-foreground gap-1"
                >
                  <Globe className="h-2.5 w-2.5" />
                  Public
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {current.description || `Kanban workflow & task board for ${current.name}`}
            </p>
          </div>
        </div>

        {/* Project Selector & Actions */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground hidden md:inline">Project:</span>
            <select
              value={current.id}
              onChange={(e) => handleProjectChange(e.target.value)}
              className="h-8 rounded-md border border-input bg-card px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.key} - {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Interactive Kanban Board */}
      {current && <KanbanBoard project={current} />}
    </div>
  )
}
