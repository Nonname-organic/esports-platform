"use client";

import { Gamepad2, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatSource = "competitive" | "tournament";

interface SourceToggleProps {
  value: StatSource;
  onChange: (v: StatSource) => void;
  className?: string;
}

/** Competitive / Tournament のデータソース切替トグル */
export function SourceToggle({ value, onChange, className }: SourceToggleProps) {
  return (
    <div className={cn("inline-flex rounded-xl border border-white/10 bg-slate-900 p-1", className)}>
      <button
        onClick={() => onChange("competitive")}
        className={cn(
          "flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-colors",
          value === "competitive" ? "bg-red-500/15 text-red-300" : "text-slate-500 hover:text-white",
        )}
      >
        <Gamepad2 className="h-3.5 w-3.5" /> Competitive
      </button>
      <button
        onClick={() => onChange("tournament")}
        className={cn(
          "flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-colors",
          value === "tournament" ? "bg-brand-500/15 text-brand-300" : "text-slate-500 hover:text-white",
        )}
      >
        <Trophy className="h-3.5 w-3.5" /> Tournament
      </button>
    </div>
  );
}
