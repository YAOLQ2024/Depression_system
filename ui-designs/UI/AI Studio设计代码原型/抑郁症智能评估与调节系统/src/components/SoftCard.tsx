import React, { ReactNode } from "react";
import { cn } from "../lib/utils";

interface SoftCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export const SoftCard: React.FC<SoftCardProps> = ({ children, className, hover = true, onClick }) => {
  return (
    <div 
      onClick={onClick}
      className={cn(
        "glass-card",
        hover && "hover:shadow-lg hover:-translate-y-0.5 cursor-pointer",
        !onClick && !hover && "cursor-default hover:shadow-soft hover:translate-y-0",
        className
      )}
    >
      {children}
    </div>
  );
}
