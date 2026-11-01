import { UserPlus, Shield, Mail } from "lucide-react"
import { useWorkspaceStore } from "@/stores/workspace-store"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

const mockMembers = [
  { id: "m-1", name: "Alex Vance", email: "alex.vance@nexus.io", role: "owner", initials: "AV" },
  { id: "m-2", name: "Elena Rostova", email: "elena@nexus.io", role: "admin", initials: "ER" },
  { id: "m-3", name: "Marcus Brody", email: "marcus@nexus.io", role: "admin", initials: "MB" },
  { id: "m-4", name: "Sarah Chen", email: "sarah@nexus.io", role: "member", initials: "SC" },
]

export function MembersPage() {
  const { currentWorkspace, setCommandPaletteOpen } = useWorkspaceStore()

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Workspace Members
          </h1>
          <p className="text-xs text-muted-foreground">
            Manage contributors, access permissions, and roles for {currentWorkspace.name}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setCommandPaletteOpen(true)}
            className="text-xs"
          >
            <UserPlus className="h-3.5 w-3.5 mr-1.5" />
            Invite Member
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {mockMembers.map((m) => (
          <Card key={m.id} className="border-border/60 bg-card/50">
            <CardContent className="p-3.5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/20 text-primary text-xs font-bold">
                    {m.initials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-foreground">{m.name}</span>
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                    <Mail className="h-3 w-3" /> {m.email}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge
                  variant={m.role === "owner" ? "default" : m.role === "admin" ? "purple" : "secondary"}
                  className="text-[10px] capitalize"
                >
                  <Shield className="h-2.5 w-2.5 mr-1" />
                  {m.role}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

