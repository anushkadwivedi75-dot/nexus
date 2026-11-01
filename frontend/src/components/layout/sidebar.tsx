import * as React from "react"
import { useLocation, Link } from "react-router-dom"
import {
  LayoutDashboard,
  FolderKanban,
  CheckSquare,
  Users,
  Settings,
  Inbox,
  Activity,
  PanelLeftClose,
  PanelLeft,
  LogOut,
  Sliders,
  ShieldCheck,
  CreditCard,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { WorkspaceSwitcher } from "@/components/layout/workspace-switcher"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import { currentUser } from "@/data/mock-data"
import { cn } from "@/lib/utils"

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
}

interface NavSection {
  title: string
  items: NavItem[]
}

const navSections: NavSection[] = [
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

export function Sidebar({ className }: { className?: string }) {
  const location = useLocation()
  const { isSidebarCollapsed, toggleSidebar, currentWorkspace } = useWorkspaceStore()

  return (
    <aside
      className={cn(
        "relative flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300 ease-in-out select-none",
        isSidebarCollapsed ? "w-14" : "w-60",
        className
      )}
    >
      {/* 1. Header: Brand Logo & Workspace Switcher */}
      <div className="flex flex-col gap-2 p-3 border-b border-sidebar-border/60">
        <div className="flex items-center justify-between">
          <Link
            to="/"
            className={cn(
              "flex items-center gap-2 overflow-hidden transition-opacity hover:opacity-90",
              isSidebarCollapsed && "justify-center w-full"
            )}
          >
            {/* Nexus Custom Geometric Logo */}
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-primary via-primary/90 to-violet-700 shadow-sm shadow-primary/20">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4 text-white"
              >
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
            </div>

            {!isSidebarCollapsed && (
              <div className="flex flex-col">
                <span className="font-semibold text-sm tracking-tight text-foreground font-mono">
                  NEXUS
                </span>
                <span className="text-[9px] uppercase tracking-wider text-muted-foreground/80 font-mono -mt-0.5">
                  Workspace
                </span>
              </div>
            )}
          </Link>

          {!isSidebarCollapsed && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={toggleSidebar}
                    className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    aria-label="Collapse sidebar"
                  >
                    <PanelLeftClose className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">Collapse sidebar</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Workspace Switcher */}
        <div className="mt-1">
          <WorkspaceSwitcher isCollapsed={isSidebarCollapsed} />
        </div>
      </div>

      {/* 2. Navigation Groups */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-0.5">
            {!isSidebarCollapsed ? (
              <div className="px-2 pb-1 text-[10px] font-semibold tracking-wider text-muted-foreground/70 uppercase">
                {section.title}
              </div>
            ) : (
              <div className="my-1.5 border-t border-sidebar-border/40" />
            )}

            <div className="space-y-0.5">
              {section.items.map((item) => {
                const isActive =
                  item.href === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(item.href)

                const Icon = item.icon

                const linkContent = (
                  <Link
                    to={item.href}
                    className={cn(
                      "group relative flex items-center gap-2.5 rounded-md px-2 py-1.5 text-xs font-medium transition-all duration-150 outline-none",
                      isActive
                        ? "bg-sidebar-accent text-foreground font-semibold shadow-xs"
                        : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-foreground",
                      isSidebarCollapsed && "justify-center px-1"
                    )}
                  >
                    {/* Active Accent Pill */}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-[2.5px] rounded-r bg-primary shadow-sm shadow-primary" />
                    )}

                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground group-hover:text-foreground"
                      )}
                    />

                    {!isSidebarCollapsed && (
                      <span className="truncate flex-1">{item.title}</span>
                    )}

                    {!isSidebarCollapsed && item.badge && (
                      <Badge
                        variant={isActive ? "default" : "secondary"}
                        className="text-[10px] px-1.5 py-0 h-4 font-mono font-normal"
                      >
                        {item.badge}
                      </Badge>
                    )}
                  </Link>
                )

                if (isSidebarCollapsed) {
                  return (
                    <TooltipProvider key={item.title} delayDuration={100}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div>{linkContent}</div>
                        </TooltipTrigger>
                        <TooltipContent side="right" className="flex items-center gap-1.5">
                          <span>{item.title}</span>
                          {item.badge && (
                            <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5">
                              {item.badge}
                            </Badge>
                          )}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )
                }

                return <div key={item.title}>{linkContent}</div>
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 3. Footer: User Profile & Expand Action */}
      <div className="border-t border-sidebar-border/60 p-2">
        {isSidebarCollapsed ? (
          <div className="flex flex-col items-center gap-1">
            <TooltipProvider delayDuration={150}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={toggleSidebar}
                    className="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-colors"
                    aria-label="Expand sidebar"
                  >
                    <PanelLeft className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">Expand sidebar</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex h-8 w-8 items-center justify-center rounded-full hover:ring-1 hover:ring-primary focus-visible:outline-none">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="bg-primary/20 text-primary text-[10px] font-bold">
                      AV
                    </AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="right" align="end" className="w-56 p-1.5">
                <DropdownMenuLabel>
                  <div className="flex flex-col">
                    <span className="text-xs font-medium text-foreground">{currentUser.name}</span>
                    <span className="text-[10px] text-muted-foreground">{currentUser.email}</span>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-xs gap-2">
                  <Sliders className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>Account Preferences</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="text-xs gap-2">
                  <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>Security & Sessions</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-xs gap-2 text-destructive focus:text-destructive">
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Log out (Mock)</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ) : (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex w-full items-center justify-between rounded-md p-1.5 hover:bg-sidebar-accent transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring text-left">
                <div className="flex items-center gap-2 min-w-0">
                  <Avatar className="h-7 w-7 shrink-0">
                    <AvatarFallback className="bg-primary/20 text-primary text-xs font-bold">
                      AV
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col min-w-0">
                    <span className="truncate text-xs font-medium text-foreground">
                      {currentUser.name}
                    </span>
                    <span className="truncate text-[10px] text-muted-foreground">
                      {currentUser.role}
                    </span>
                  </div>
                </div>

                <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 uppercase tracking-wider text-muted-foreground">
                  {currentWorkspace.role}
                </Badge>
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" side="top" className="w-56 p-1.5">
              <DropdownMenuLabel className="px-2 py-1.5">
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-foreground">{currentUser.name}</span>
                  <span className="text-[10px] text-muted-foreground">{currentUser.email}</span>
                </div>
              </DropdownMenuLabel>

              <DropdownMenuSeparator />

              <DropdownMenuItem className="text-xs gap-2 cursor-pointer">
                <Sliders className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Account Preferences</span>
              </DropdownMenuItem>

              <DropdownMenuItem className="text-xs gap-2 cursor-pointer">
                <ShieldCheck className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Security & Sessions</span>
              </DropdownMenuItem>

              <DropdownMenuItem className="text-xs gap-2 cursor-pointer">
                <CreditCard className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Billing ({currentWorkspace.plan})</span>
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem className="text-xs gap-2 text-destructive focus:text-destructive cursor-pointer">
                <LogOut className="h-3.5 w-3.5" />
                <span>Log out (Mock)</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </aside>
  )
}

