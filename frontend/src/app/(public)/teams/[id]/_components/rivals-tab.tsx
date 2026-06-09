"use client";

import Link from "next/link";
import { Swords, AlertCircle, ChevronRight } from "lucide-react";
import { useTeamRivals } from "@/features/career/hooks/use-career";
import { cn } from "@/lib/utils";

interface RivalsTabProps {
  teamId: string;
}

export function RivalsTab({ teamId }: RivalsTabProps) {
  const { data: rivals, isLoading, isError } = useTeamRivals(teamId);

  if (isLoading) {
    return (
      <div className="space-y-2 pt-6">
        {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-white/5" />)}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-48 flex-col items-center justify-center pt-6">
        <AlertCircle className="mb-3 h-10 w-10 text-slate-700" />
        <p className="text-sm text-slate-500">対戦履歴の読み込みに失敗しました</p>
      </div>
    );
  }

  if (!rivals || rivals.length === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Swords className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">対戦履歴がありません</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 pt-6">
      <p className="mb-3 text-xs text-slate-500">対戦頻度の高い相手TOP{rivals.length}</p>
      {rivals.map((r) => {
        const pct = Math.round(r.win_rate * 100);
        const dominant = pct >= 60;
        const losing = pct < 40;
        return (
          <Link
            key={r.team_id}
            href={`/teams/${r.team_id}`}
            className="flex items-center gap-4 rounded-xl border border-white/8 bg-slate-900 px-4 py-3 hover:border-white/15 transition-colors"
          >
            <div className="h-9 w-9 flex-shrink-0 rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
              <span className="text-xs font-bold text-slate-500">{r.team_tag.slice(0, 3)}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-white">{r.team_name}</p>
              <p className="text-xs text-slate-500">{r.matches}回対戦</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-bold">
                <span className="text-green-400">{r.wins}</span>
                <span className="text-slate-600"> - </span>
                <span className="text-red-400">{r.losses}</span>
              </p>
              <p className={cn("text-xs font-semibold", dominant ? "text-green-400" : losing ? "text-red-400" : "text-slate-400")}>
                勝率 {pct}%
              </p>
            </div>
            <ChevronRight className="h-4 w-4 flex-shrink-0 text-slate-600" />
          </Link>
        );
      })}
    </div>
  );
}
