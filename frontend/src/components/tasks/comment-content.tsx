import React from "react"

interface CommentContentProps {
  content: string
  isDeleted?: boolean
  className?: string
}

export const CommentContent: React.FC<CommentContentProps> = ({
  content,
  isDeleted = false,
  className = "",
}) => {
  if (isDeleted) {
    return (
      <p className={`text-xs text-muted-foreground/70 italic select-none ${className}`}>
        [This comment has been deleted.]
      </p>
    )
  }

  // Tokenize and render text with safe formatting for mentions, inline code, bold, italic
  const renderFormattedLine = (line: string, lineIdx: number) => {
    // Regex matches:
    // 1. Explicit mention: @[Name](uuid)
    // 2. Simple handle: @username
    // 3. Inline code: `code`
    // 4. Bold: **text**
    // 5. Italic: *text*
    const tokenRegex = /(@\[([^\]]+)\]\([a-f0-9\-]{36}\)|@([a-zA-Z0-9_.-]+)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*)/g

    const elements: React.ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = tokenRegex.exec(line)) !== null) {
      // Append text before match
      if (match.index > lastIndex) {
        elements.push(line.substring(lastIndex, match.index))
      }

      const fullMatch = match[0]

      if (fullMatch.startsWith("@[")) {
        // Explicit mention @[Name](id)
        const name = match[2]
        elements.push(
          <span
            key={`mention-${lineIdx}-${match.index}`}
            className="inline-flex items-center rounded bg-primary/15 px-1 py-0.2 text-[11px] font-semibold text-primary border border-primary/20 select-none mx-0.5"
          >
            @{name}
          </span>
        )
      } else if (fullMatch.startsWith("@")) {
        // Simple handle @username
        const handle = match[3]
        elements.push(
          <span
            key={`handle-${lineIdx}-${match.index}`}
            className="inline-flex items-center rounded bg-primary/10 px-1 py-0.2 text-[11px] font-medium text-primary border border-primary/20 select-none mx-0.5"
          >
            @{handle}
          </span>
        )
      } else if (fullMatch.startsWith("`")) {
        // Inline code `code`
        const codeText = match[4]
        elements.push(
          <code
            key={`code-${lineIdx}-${match.index}`}
            className="rounded bg-muted px-1 py-0.5 font-mono text-[11px] text-foreground border border-border/40"
          >
            {codeText}
          </code>
        )
      } else if (fullMatch.startsWith("**")) {
        // Bold
        const boldText = match[5]
        elements.push(
          <strong key={`bold-${lineIdx}-${match.index}`} className="font-semibold text-foreground">
            {boldText}
          </strong>
        )
      } else if (fullMatch.startsWith("*")) {
        // Italic
        const italicText = match[6]
        elements.push(
          <em key={`italic-${lineIdx}-${match.index}`} className="italic text-foreground/90">
            {italicText}
          </em>
        )
      }

      lastIndex = tokenRegex.lastIndex
    }

    if (lastIndex < line.length) {
      elements.push(line.substring(lastIndex))
    }

    return (
      <span key={`line-${lineIdx}`} className="block min-h-[1.25rem]">
        {elements.length > 0 ? elements : <br />}
      </span>
    )
  }

  const lines = content.split("\n")

  return (
    <div className={`text-xs leading-relaxed text-foreground break-words space-y-1 ${className}`}>
      {lines.map((line, idx) => renderFormattedLine(line, idx))}
    </div>
  )
}

