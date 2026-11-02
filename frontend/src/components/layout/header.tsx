import { useLocation } from "react-router-dom"
import {
  Menu,
  Search,
  Bell,
  Command as CommandIcon,
  Plus,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { useAuthStore } from "@/stores/auth-store"
import { Button } from "@/components/ui/button"
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

const pageTitles: Record<string, { title: string; category: string }> = {
  "/": { title: "Overview", category: "Workspace" },
  "/projects": { title: "Projects Roadmap", category: "Workspace" },
  "/tasks": { title: "My Tasks", category: "Workspace" },
  "/members": { title: "Team Members", category: "Manage" },
  "/settings": { title: "Settings", category: "Manage" },
  "/inbox": { title: "Inbox", category: "Personal" },
  "/activity": { title: "Activity Feed", category: "Personal" },
}

export function Header() {
  const location = useLocation()
  const { currentWorkspace, setCommandPaletteOpen, setMobileSidebarOpen } =
    useWorkspaceStore()
  const { user, logout } = useAuthStore()

  const displayName = user?.full_name || user?.name || currentUser.name || "User"
  const displayEmail = user?.email || currentUser.email || ""
  const initials = (displayName || "User")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .substring(0, 2) || "NX"

  const currentRoute = pageTitles[location.pathname] || {
    title: "Overview",
    category: "Workspace",
  }

  return (
    <header className="sticky top-0 z-30 flex h-12 w-full items-center justify-between border-b border-border/70 bg-background/80 px-4 backdrop-blur-md select-none">
      {/* Left: Mobile Menu & Breadcrumbs */}
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger Trigger */}
        <Button
          variant="ghost"
          size="icon-sm"
          className="md:hidden text-muted-foreground hover:text-foreground"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label="Open navigation menu"
        >
          <Menu className="h-4 w-4" />
        </Button>

        {/* Breadcrumb Hierarchy */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className="font-medium text-muted-foreground hidden sm:inline">
            {currentWorkspace.name}
          </span>
          <span className="text-muted-foreground/40 hidden sm:inline">/</span>
          <span className="text-muted-foreground/80 hidden sm:inline">
            {currentRoute.category}
          </span>
          <span className="text-muted-foreground/40 hidden sm:inline">/</span>
          <span className="font-semibold text-foreground tracking-tight">
            {currentRoute.title}
          </span>
        </div>
      </div>

      {/* Right: Search, Notifications & Profile */}
      <div className="flex items-center gap-2">
        {/* Command Palette Trigger */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex h-8 items-center gap-2 rounded-md border border-border/60 bg-card/40 px-2.5 text-xs text-muted-foreground hover:border-border hover:bg-card hover:text-foreground transition-all shadow-2xs"
          aria-label="Search or run command"
        >
          <Search className="h-3.5 w-3.5 text-muted-foreground/80" />
          <span className="hidden sm:inline-block pr-4">Search or command...</span>
          <span className="sm:hidden">Search</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-border/80 bg-muted/60 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground/90 font-medium">
            <CommandIcon className="h-2.5 w-2.5" /> K
          </kbd>
        </button>

        {/* Quick Create Task Button */}
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="subtle"
                size="sm"
                className="hidden sm:flex items-center gap-1.5 text-xs h-8 px-2.5"
                onClick={() => setCommandPaletteOpen(true)}
              >
                <Plus className="h-3.5 w-3.5 text-primary" />
                <span className="font-medium">New Issue</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Create issue (Cmd+K)</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Notifications Popover Trigger */}
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                className="relative text-muted-foreground hover:text-foreground"
                aria-label="Notifications"
              >
                <Bell className="h-4 w-4" />
                <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                </span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>3 unread notifications</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Profile Avatar Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex h-7 w-7 items-center justify-center rounded-full hover:ring-1 hover:ring-primary focus-visible:outline-none">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="bg-primary/20 text-primary text-[10px] font-bold">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-52 p-1.5">
            <DropdownMenuLabel className="px-2 py-1.5">
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-foreground">{displayName}</span>
                <span className="text-[10px] text-muted-foreground">{displayEmail}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-xs">Profile settings</DropdownMenuItem>
            <DropdownMenuItem className="text-xs flex justify-between">
              <span>Theme</span>
              <Badge variant="secondary" className="text-[9px] px-1 py-0 h-4">Dark-First</Badge>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => logout()}
              className="text-xs text-destructive focus:text-destructive cursor-pointer"
            >
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

