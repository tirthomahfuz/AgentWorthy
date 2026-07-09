import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "lg" | "sm";
}

export function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50",
        variant === "default" && "bg-accent text-accent-foreground hover:bg-accent/90",
        variant === "outline" && "border border-border bg-transparent hover:bg-muted",
        variant === "ghost" && "hover:bg-muted",
        size === "default" && "h-10 px-4 py-2 text-sm",
        size === "lg" && "h-12 px-8 text-base",
        size === "sm" && "h-8 px-3 text-xs",
        className
      )}
      {...props}
    />
  );
}
