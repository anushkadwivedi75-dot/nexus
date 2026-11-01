import { useLocation, Link } from "react-router-dom"
import {
  LayoutDashboard,
  FolderKanban,
  CheckSquare,
  Users,
  Settings,
  Inbox,
  Activity,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { WorkspaceSwitcher } from "@/components/layout/workspace-switcher"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { currentUser } from "@/data/mock-data"
import { cn } from "@/lib/utils"

export function MobileNav() {
  const location = useLocation()
  const { isMobileSidebarOpen, setMobileSidebarOpen, currentWorkspace } =
    useWorkspaceStore()

  const navSections = [
    {
      title: "Workspace",
      items: [
        { title: "Overview", href: "/", icon: LayoutDashboard },
        { title: "Projects", href: "/projects", icon: FolderKanban, badge: "4" },
        { title: "My Tasks", href: "/tasks", icon: CheckSquare, badge: "8" },
      ],
    },
    {
      title: "Manage",
      items: [
        { title: "Members", href: "/members", icon: Users },
        { title: "Settings", href: "/settings", icon: Settings },
      ],
    },
    {
      title: "Personal",
      items: [
        { title: "Inbox", href: "/inbox", icon: Inbox, badge: "3" },
        { title: "Activity", href: "/activity", icon: Activity },
      ],
    },
  ]

  return (
    <Sheet open={isMobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
      <SheetContent side="left" className="w-72 p-0 flex flex-col bg-sidebar border-r border-sidebar-border">
        {/* Header */}
        <SheetHeader className="p-4 border-b border-sidebar-border/60 text-left">
          <div className="flex items-center gap-2 mb-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-primary text-white">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="h-3.5 w-3.5">
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
            </div>
            <SheetTitle className="text-sm font-semibold tracking-wider font-mono">
              NEXUS
            </SheetTitle>
          </div>

          <WorkspaceSwitcher isCollapsed={false} />
        </SheetHeader>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1">
              <div className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                {section.title}
              </div>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const isActive =
                    item.href === "/"
                      ? location.pathname === "/"
                      : location.pathname.startsWith(item.href)
                  const Icon = item.icon

                  return (
                    <Link
                      key={item.title}
                      to={item.href}
                      onClick={() => setMobileSidebarOpen(false)}
                      className={cn(
                        "flex items-center justify-between rounded-md px-2.5 py-2 text-xs font-medium transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-foreground font-semibold"
                          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
                      )}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className={cn("h-4 w-4", isActive ? "text-primary" : "text-muted-foreground")} />
                        <span>{item.title}</span>
                      </div>
                      {item.badge && (
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                          {item.badge}
                        </Badge>
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Footer */}
        <div className="border-t border-sidebar-border/60 p-3 bg-sidebar-accent/30">
          <div className="flex items-center gap-2">
            <Avatar className="h-7 w-7">
              <AvatarFallback className="bg-primary/20 text-primary text-xs font-bold">
                AV
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="truncate text-xs font-medium text-foreground">{currentUser.name}</span>
              <span className="truncate text-[10px] text-muted-foreground">{currentUser.email}</span>
            </div>
            <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 uppercase">
              {currentWorkspace.role}
            </Badge>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

