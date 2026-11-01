import { CheckCircle2, AtSign } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

const mockNotifications = [
  {
    id: "notif-1",
    author: "Sarah Chen",
    action: "mentioned you in a comment on",
    target: "CORE-104 (Deterministic two-column status locks)",
    time: "12m ago",
    unread: true,
  },
  {
    id: "notif-2",
    author: "Marcus Brody",
    action: "assigned you to",
    target: "AUTH-89 (Verify crash-safe refresh grace-chain)",
    time: "45m ago",
    unread: true,
  },
  {
    id: "notif-3",
    author: "Elena Rostova",
    action: "approved your review on",
    target: "UI-15 (Collapsible left sidebar)",
    time: "2h ago",
    unread: true,
  },
  {
    id: "notif-4",
    author: "Nexus System",
    action: "successfully migrated workspace database schema to",
    target: "v1.3.1 (Engine Constraints)",
    time: "1d ago",
    unread: false,
  },
]

export function InboxPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/50 pb-5">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Notification Inbox
          </h1>
          <p className="text-xs text-muted-foreground">
            Mentions, assignments, and real-time project alerts
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="text-xs">
            <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
            Mark all read
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {mockNotifications.map((n) => (
          <Card
            key={n.id}
            className={`border-border/60 transition-colors ${
              n.unread ? "bg-card/90 border-border" : "bg-card/40 opacity-75"
            }`}
          >
            <CardContent className="p-3.5 flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-0.5">
                  {n.author.includes("System") ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <AtSign className="h-3.5 w-3.5" />
                  )}
                </div>

                <div className="flex flex-col space-y-0.5">
                  <p className="text-xs text-foreground">
                    <strong className="font-semibold">{n.author}</strong>{" "}
                    <span className="text-muted-foreground">{n.action}</span>{" "}
                    <span className="font-medium text-foreground">{n.target}</span>
                  </p>
                  <span className="text-[10px] text-muted-foreground">{n.time}</span>
                </div>
              </div>

              {n.unread && (
                <span className="h-2 w-2 rounded-full bg-primary shrink-0 mt-1.5" />
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
