import * as React from "react"
import { useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  FolderKanban,
  CheckSquare,
  Users,
  Settings,
  Inbox,
  Plus,
  Moon,
  Sparkles,
} from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"
import { mockProjects } from "@/data/mock-data"

export function CommandPalette() {
  const navigate = useNavigate()
  const { isCommandPaletteOpen, setCommandPaletteOpen, currentWorkspace } =
    useWorkspaceStore()

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setCommandPaletteOpen(!isCommandPaletteOpen)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [isCommandPaletteOpen, setCommandPaletteOpen])

  const runCommand = (command: () => void) => {
    setCommandPaletteOpen(false)
    command()
  }

  return (
    <CommandDialog open={isCommandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <CommandInput placeholder={`Search ${currentWorkspace.name} or type a command...`} />
      <CommandList>
        <CommandEmpty>No matching commands or projects found.</CommandEmpty>

        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => runCommand(() => navigate("/"))}>
            <LayoutDashboard className="mr-2 h-4 w-4 text-primary" />
            <span>Overview Dashboard</span>
            <CommandShortcut>G O</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => navigate("/projects"))}>
            <FolderKanban className="mr-2 h-4 w-4 text-primary" />
            <span>Projects Roadmap</span>
            <CommandShortcut>G P</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => navigate("/tasks"))}>
            <CheckSquare className="mr-2 h-4 w-4 text-primary" />
            <span>My Active Tasks</span>
            <CommandShortcut>G T</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => navigate("/inbox"))}>
            <Inbox className="mr-2 h-4 w-4 text-primary" />
            <span>Inbox & Notifications</span>
            <CommandShortcut>G I</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => navigate("/members"))}>
            <Users className="mr-2 h-4 w-4 text-primary" />
            <span>Team Members</span>
            <CommandShortcut>G M</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => navigate("/settings"))}>
            <Settings className="mr-2 h-4 w-4 text-primary" />
            <span>Workspace Settings</span>
            <CommandShortcut>G S</CommandShortcut>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Active Projects">
          {mockProjects.map((prj) => (
            <CommandItem
              key={prj.id}
              onSelect={() => runCommand(() => navigate("/projects"))}
            >
              <div
                className="mr-2 h-2.5 w-2.5 rounded-full shrink-0"
                style={{ backgroundColor: prj.colorHex }}
              />
              <span className="font-mono text-[11px] text-muted-foreground mr-1.5">
                {prj.key}
              </span>
              <span>{prj.name}</span>
              <span className="ml-auto text-[10px] text-muted-foreground capitalize">
                {prj.status}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Quick Actions">
          <CommandItem onSelect={() => runCommand(() => navigate("/tasks"))}>
            <Plus className="mr-2 h-4 w-4 text-muted-foreground" />
            <span>Create new task (Mock)</span>
            <CommandShortcut>C</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => navigate("/projects"))}>
            <Sparkles className="mr-2 h-4 w-4 text-muted-foreground" />
            <span>Create new project (Mock)</span>
            <CommandShortcut>P</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => {})}>
            <Moon className="mr-2 h-4 w-4 text-muted-foreground" />
            <span>Toggle Dark Mode (Dark-First Default)</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
