import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/cn"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-accent text-white",
        secondary: "border-transparent bg-surface-2 text-ink",
        destructive: "border-transparent bg-accent-danger text-white",
        outline: "text-ink",
        success: "border-transparent bg-accent-success text-white",
        warning: "border-transparent bg-accent-warning text-white",
        // Tint variants — transparent backgrounds + matching text + soft border
        "tint-success": "border-success/30 bg-success/10 text-success",
        "tint-danger": "border-danger/30 bg-danger/10 text-danger",
        "tint-warning": "border-warning/30 bg-warning/10 text-warning",
        "tint-info": "border-accent-info/30 bg-accent-info/10 text-accent-info",
        "tint-accent": "border-accent/30 bg-accent/10 text-accent",
        "tint-secondary": "border-accent-secondary/30 bg-accent-secondary/10 text-accent-secondary",
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
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
