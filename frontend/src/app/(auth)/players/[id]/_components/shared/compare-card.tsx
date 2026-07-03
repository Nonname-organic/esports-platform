import { Gamepad2, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CompareRow {
  label: string;
  competitive: string;
  tournament: string;
  /** どちらが優位か（数値の大小で色付け） */
  compBetter?: boolean | null;
}

interface CompareCardProps {
  rows: CompareRow[];
}

/** Competitive と Tournament を横並びで比較するカード */
export function CompareCard({ rows }: CompareCardProps) {
  return (
    <section className="overflow-hidden rounded-xl border border-white/10 bg-slate-900">
      {/* ヘッダー */}
      <div className="grid grid-cols-[1fr_auto_auto] items-center gap-2 border-b border-white/10 px-5 py-3">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">指標</span>
        <span className="flex w-24 items-center justify-center gap-1 text-xs font-bold text-red-300">
          <Gamepad2 className="h-3.5 w-3.5" /> Comp
        </span>
        <span className="flex w-24 items-center justify-center gap-1 text-xs font-bold text-brand-300">
          <Trophy className="h-3.5 w-3.5" /> Tourney
        </span>
      </div>
      {/* 行 */}
      <div className="divide-y divide-white/5">
        {rows.map((r) => (
          <div key={r.label} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 px-5 py-3">
            <span className="text-sm text-slate-400">{r.label}</span>
            <span
              className={cn(
                "w-24 text-center text-sm font-bold tabular-nums",
                r.compBetter === true ? "text-green-400" : r.compBetter === false ? "text-slate-300" : "text-white",
              )}
            >
              {r.competitive}
            </span>
            <span
              className={cn(
                "w-24 text-center text-sm font-bold tabular-nums",
                r.compBetter === false ? "text-green-400" : r.compBetter === true ? "text-slate-300" : "text-white",
              )}
            >
              {r.tournament}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
