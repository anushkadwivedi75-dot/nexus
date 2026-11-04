import { useEffect, useState } from "react"
import { realTimeClient, type ConnectionStatus } from "@/services/websocket-client"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export function RealTimeStatusPill({ className = "" }: { className?: string }) {
  const [status, setStatus] = useState<ConnectionStatus>(realTimeClient.getStatus())

  useEffect(() => {
    return realTimeClient.onStatusChange((newStatus) => {
      setStatus(newStatus)
    })
  }, [])

  let dotColor = "bg-emerald-500"
  let pingColor = "bg-emerald-400"
  let label = "Live"
  let tooltipText = "Real-time sync active (WebSocket connected)"
  let showPing = true

  if (status === "connecting") {
    dotColor = "bg-amber-500"
    pingColor = "bg-amber-400"
    label = "Connecting"
    tooltipText = "Acquiring handshake ticket and establishing connection..."
    showPing = true
  } else if (status === "reconnecting") {
    dotColor = "bg-amber-500"
    pingColor = "bg-amber-400"
    label = "Reconnecting"
    tooltipText = "Reconnecting to real-time engine with exponential backoff..."
    showPing = true
  } else if (status === "disconnected") {
    dotColor = "bg-zinc-500"
    pingColor = ""
    label = "Offline"
    tooltipText = "Real-time offline. Automatic REST reconciliation active on reconnect."
    showPing = false
  }

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={`inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/30 px-2 py-0.5 text-[10px] font-medium tracking-tight select-none transition-colors ${className}`}
            role="status"
            aria-live="polite"
          >
            <span className="relative flex h-2 w-2">
              {showPing && (
                <span
                  className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${pingColor}`}
                />
              )}
              <span className={`relative inline-flex h-2 w-2 rounded-full ${dotColor}`} />
            </span>
            <span className="text-muted-foreground">{label}</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          {tooltipText}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

