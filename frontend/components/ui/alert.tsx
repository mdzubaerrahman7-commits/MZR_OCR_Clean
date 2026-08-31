import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Alert({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive", className)} {...props} />;
}
