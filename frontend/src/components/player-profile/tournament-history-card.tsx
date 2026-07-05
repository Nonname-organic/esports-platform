"use client";

import Link from "next/link";
import { History, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePlayerHistory } from "@/features/player-profile/hooks/use-player-profile";

const PLACEMENT: Record<string, { label: string; cls: string }> = {
  champion: { label: "優勝", cls: "bg-yellow-500/15 text-yellow-400" },
  runner_up: { label: "準優勝", cls: "bg-slate-300/10 text-slate-300" },
  top4: { label: "ベスト4", cls: "bg-amber-700/15 text-amber-500" },
  participated: { label: "参加", cls: "bg-white/5 text-slate-400" },
};

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("ja-JP", { year: "numeric", month: "short" });
}

/** Tournament History: 大会履歴タイムライン（placement / team / date）。 */
export function TournamentHistoryCard({ playerId }: { playerId: string }) {
  const { data: items } = usePlayerHistory(playerId);
  if (!items || items.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
        <History className="h-4 w-4 text-brand-400" /> Tournament History
      </h2>
      <ul className="relative space-y-3 border-l border-white/10 pl-5">
        {items.map((h) => {
          const p = h.placement ? PLACEMENT[h.placement] ?? PLACEMENT.participated : PLACEMENT.participated;
          return (
            <li key={h.tournament_id} className="relative">
              <span className="absolute -left-[1.42rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-brand-500 bg-slate-950" />
              <Link
                href={`/tournaments/${h.tournament_id}`}
                className="group flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/[0.03]"
              >
                <span className={cn("flex-shrink-0 rounded-md px-2 py-0.5 text-[11px] font-bold", p.cls)}>{p.label}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-white group-hover:text-brand-400">{h.tournament_name}</span>
                  {h.team_name && <span className="text-xs text-slate-500">{h.team_name}</span>}
                </span>
                {h.is_mvp && <Star className="h-3.5 w-3.5 flex-shrink-0 text-pink-400" />}
                <span className="flex-shrink-0 text-xs text-slate-500">{fmtDate(h.ended_at)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
