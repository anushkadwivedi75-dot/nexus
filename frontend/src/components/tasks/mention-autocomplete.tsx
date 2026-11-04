import React, { useEffect, useState } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

export interface MentionableMember {
  id: string
  full_name?: string
  email?: string
  avatar_url?: string | null
}

interface MentionAutocompleteProps {
  members: MentionableMember[]
  filterText: string
  onSelect: (member: MentionableMember) => void
  onClose: () => void
}

export const MentionAutocomplete: React.FC<MentionAutocompleteProps> = ({
  members,
  filterText,
  onSelect,
  onClose,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0)

  const cleanQuery = filterText.toLowerCase().trim()
  const filtered = members.filter((m) => {
    if (!cleanQuery) return true
    const nameMatch = m.full_name?.toLowerCase().includes(cleanQuery)
    const emailMatch = m.email?.toLowerCase().includes(cleanQuery)
    return nameMatch || emailMatch
  }).slice(0, 5)

  useEffect(() => {
    setSelectedIndex(0)
  }, [filterText])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (filtered.length === 0) return

      if (e.key === "ArrowDown") {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % filtered.length)
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % filtered.length)
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault()
        if (filtered[selectedIndex]) {
          onSelect(filtered[selectedIndex])
        }
      } else if (e.key === "Escape") {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [filtered, selectedIndex, onSelect, onClose])

  if (filtered.length === 0) return null

  return (
    <div
      className="absolute bottom-full mb-1 left-0 z-50 w-64 rounded-md border border-border bg-popover p-1 shadow-lg backdrop-blur-md"
      role="listbox"
      aria-label="Member mentions"
    >
      <div className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        Mention Member
      </div>
      {filtered.map((member, index) => {
        const isSelected = index === selectedIndex
        const initials = (member.full_name || member.email || "U")
          .split(" ")
          .map((n) => n[0])
          .join("")
          .toUpperCase()
          .slice(0, 2)

        return (
          <div
            key={member.id}
            onClick={() => onSelect(member)}
            onMouseEnter={() => setSelectedIndex(index)}
            className={`flex items-center gap-2 rounded px-2 py-1.5 text-xs cursor-pointer select-none transition-colors ${
              isSelected ? "bg-accent text-accent-foreground font-medium" : "text-popover-foreground hover:bg-muted/50"
            }`}
            role="option"
            aria-selected={isSelected}
          >
            <Avatar className="h-5 w-5 text-[9px]">
              <AvatarFallback className="bg-primary/20 text-primary">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col overflow-hidden min-w-0">
              <span className="truncate text-xs leading-none">
                {member.full_name || member.email?.split("@")[0]}
              </span>
              {member.email && (
                <span className="truncate text-[10px] text-muted-foreground leading-tight mt-0.5">
                  {member.email}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

