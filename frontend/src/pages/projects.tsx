import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Plus,
  Search,
  Users,
  Lock,
  Globe,
  Kanban,
  Calendar,
  Layers,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { useProjectStore } from "@/stores/project-store"
import type { Project } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CreateProjectDialog, ProjectMembersDialog } from "@/components/projects/project-dialogs"
import { RoadmapView } from "@/components/projects/roadmap-view"

export function ProjectsPage() {
  const navigate = useNavigate()
  const { currentWorkspace } = useWorkspaceStore()
  const {
    projects,
    activeProject,
    isLoadingProjects,
    fetchProjects,
    setActiveProject,
    createProject,
  } = useProjectStore()

  const [search, setSearch] = useState("")
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [memberProject, setMemberProject] = useState<Project | null>(null)
  const [isMemberDialogOpen, setIsMemberDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("projects")

  useEffect(() => {
    if (currentWorkspace?.id) {
      fetchProjects(currentWorkspace.id)
    }
  }, [currentWorkspace?.id])

  const filteredProjects = projects.filter((p) => {
    const q = search.toLowerCase()
    return p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q)
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Projects & Roadmaps
          </h1>
          <p className="text-xs text-muted-foreground">
            Track multi-project velocity, milestone delivery, and access controls for {currentWorkspace.name}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setIsCreateOpen(true)}
            className="text-xs h-8"
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Project
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <TabsList className="bg-muted/50 p-1">
            <TabsTrigger value="projects" className="text-xs gap-1.5">
              <Layers className="h-3.5 w-3.5" />
              All Projects ({projects.length})
            </TabsTrigger>
            <TabsTrigger value="roadmap" className="text-xs gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              Roadmap Schedule
            </TabsTrigger>
          </TabsList>

          {activeTab === "projects" && (
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                placeholder="Filter by key or name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 h-8 text-xs"
              />
            </div>
          )}
        </div>

        {/* Tab 1: Project Cards Grid */}
        <TabsContent value="projects" className="space-y-4 m-0">
          {isLoadingProjects ? (
            <div className="flex h-48 items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 p-12 text-center">
              <Layers className="mx-auto h-8 w-8 text-muted-foreground/50 mb-3" />
              <h4 className="text-sm font-semibold text-foreground mb-1">
                {search ? "No matching projects found" : "No projects created yet"}
              </h4>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto mb-4">
                {search
                  ? "Try adjusting your search query."
                  : "Create your first project to start organizing tasks, roadmaps, and custom Kanban workflows."}
              </p>
              {!search && (
                <Button size="sm" onClick={() => setIsCreateOpen(true)} className="text-xs">
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  Create Project
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredProjects.map((prj) => (
                <Card
                  key={prj.id}
                  className="group border-border/70 bg-card/60 hover:border-primary/50 transition-all flex flex-col justify-between"
                >
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-muted/80 text-foreground">
                          {prj.key}
                        </span>
                        <h3 className="font-semibold text-xs text-foreground truncate max-w-[150px]">
                          {prj.name}
                        </h3>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {prj.is_private ? (
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
                    </div>

                    <p className="text-xs text-muted-foreground line-clamp-2 min-h-[32px]">
                      {prj.description || "No description provided."}
                    </p>

                    <div className="flex items-center justify-between text-xs pt-2 border-t border-border/40 text-muted-foreground">
                      <span>
                        <strong className="text-foreground">{prj.task_counter}</strong> total tasks
                      </span>
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {prj.status}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      <Button
                        size="sm"
                        className="flex-1 text-xs h-8 gap-1.5"
                        onClick={() => {
                          setActiveProject(prj)
                          navigate(`/projects/${prj.id}`)
                        }}
                      >
                        <Kanban className="h-3.5 w-3.5" />
                        Open Board
                      </Button>

                      {prj.is_private && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs h-8 px-2.5"
                          title="Manage private project members"
                          onClick={() => {
                            setMemberProject(prj)
                            setIsMemberDialogOpen(true)
                          }}
                        >
                          <Users className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Roadmap Timeline */}
        <TabsContent value="roadmap" className="space-y-4 m-0">
          {projects.length > 0 ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-muted-foreground">Active Project:</label>
                <select
                  value={activeProject?.id || projects[0]?.id}
                  onChange={(e) => {
                    const found = projects.find((p) => p.id === e.target.value)
                    if (found) setActiveProject(found)
                  }}
                  className="rounded-md border border-input bg-card px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.key} - {p.name}
                    </option>
                  ))}
                </select>
              </div>

              {activeProject ? (
                <RoadmapView
                  projectId={activeProject.id}
                  projectKey={activeProject.key}
                />
              ) : (
                <RoadmapView
                  projectId={projects[0].id}
                  projectKey={projects[0].key}
                />
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-muted-foreground">
              Create a project to view its roadmap timeline.
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Create Project Modal */}
      <CreateProjectDialog
        isOpen={isCreateOpen}
        workspaceId={currentWorkspace.id}
        onClose={() => setIsCreateOpen(false)}
        onCreate={async (data) => {
          await createProject(currentWorkspace.id, data)
        }}
      />

      {/* Private Project Members Modal */}
      <ProjectMembersDialog
        project={memberProject}
        workspaceId={currentWorkspace.id}
        isOpen={isMemberDialogOpen}
        onClose={() => {
          setIsMemberDialogOpen(false)
          setMemberProject(null)
        }}
      />
    </div>
  )
}
