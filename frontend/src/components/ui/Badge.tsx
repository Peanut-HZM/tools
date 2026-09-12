import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/cn"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border border-glass-border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2",
  {
    variants: {
      variant: {
        // 中性 variant：玻璃底 + ink 文字（亮/暗主题均可读）
        default: "bg-glass-bg text-ink",
        secondary: "bg-glass-bg text-ink",
        outline: "text-ink",
        // 语义 variant：低饱和语义色底 + 语义色文字 + 同色软描边（与 tint 图标同思路，
        // 保证亮/暗双主题可读；border 宽度由 base 的 border 提供，这里只覆盖颜色）
        destructive: "bg-[rgba(248,113,113,0.12)] text-accent-danger border-[rgba(248,113,113,0.3)]",
        success: "bg-[rgba(52,211,153,0.12)] text-accent-success border-[rgba(52,211,153,0.3)]",
        warning: "bg-[rgba(251,191,36,0.12)] text-accent-warning border-[rgba(251,191,36,0.3)]",
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
