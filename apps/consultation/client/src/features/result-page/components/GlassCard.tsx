import type { ReactNode } from "react";
import { cn } from "../../../lib/utils";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

export function GlassCard({ children, className, onClick, hoverable = false }: GlassCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-[10px] border border-white/18 bg-[linear-gradient(180deg,rgba(9,18,34,0.34),rgba(9,18,34,0.2))] shadow-[0_16px_36px_rgba(15,23,42,0.2)] backdrop-blur-[18px] saturate-[135%]",
        hoverable &&
          "cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:border-white/24 hover:bg-[linear-gradient(180deg,rgba(15,23,42,0.42),rgba(15,23,42,0.24))] hover:shadow-[0_18px_42px_rgba(15,23,42,0.26)]",
        className,
      )}
    >
      {children}
    </div>
  );
}
