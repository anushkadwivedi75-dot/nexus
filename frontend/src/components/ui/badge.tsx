import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium tracking-wide transition-colors focus:outline-none focus:ring-1 focus:ring-ring select-none",
  {
    variants: {
      variant: {
        default:
          "border border-primary/30 bg-primary/10 text-primary-foreground",
        secondary:
          "border border-border/80 bg-secondary/60 text-secondary-foreground",
        destructive:
          "border border-destructive/30 bg-destructive/15 text-destructive",
        outline:
          "border border-border text-foreground",
        success:
          "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        warning:
          "border border-amber-500/30 bg-amber-500/10 text-amber-400",
        purple:
          "border border-violet-500/30 bg-violet-500/15 text-violet-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
