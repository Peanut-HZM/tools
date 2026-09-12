import { cn } from "@/lib/cn"

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  // 底色用玻璃表面（bg-glass-bg），保留呼吸动画
  return <div className={cn("animate-pulse rounded-md bg-glass-bg", className)} {...props} />
}

export { Skeleton }
