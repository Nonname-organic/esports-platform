"use client";

import { RotateCcw, Filter } from "lucide-react";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { useTournaments } from "@/features/tournaments/hooks/use-tournaments";
import { cn, getGameColor } from "@/lib/utils";
import type { GameType } from "@/types/tournament";
import type { AnalyticsPeriod } from "@/types/analytics";

const GAMES: GameType[] = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];

const PERIODS: { value: AnalyticsPeriod; label: string }[] = [
  { value: "7d", label: "7日" },
  { value: "30d", label: "30日" },
  { value: "90d", label: "90日" },
  { value: "all", label: "全期間" },
];

export function FilterBar() {
  const {
    game, tournamentId, dateFrom, dateTo, period,
    setGame, setTournamentId, setDateFrom, setDateTo, setPeriod, reset,
  } = useAnalyticsFilterStore();

  const { data: tournamentsData } = useTournaments();
  const tournaments = tournamentsData?.pages.flatMap((p) => p.data) ?? [];
  const filteredTournaments = tournaments.filter((t) => t.game === game);

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3 backdrop-blur">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
          <Filter className="h-3.5 w-3.5" />
          フィルター
        </div>

        {/* ゲーム */}
        <div className="flex items-center gap-1 rounded-lg border border-white/8 bg-white/3 p-0.5">
          {GAMES.map((g) => (
            <button
              key={g}
              onClick={() => { setGame(g); setTournamentId(""); }}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors",
                game === g ? "bg-brand-500 text-white shadow-sm" : "text-slate-500 hover:text-white",
              )}
            >
              {g}
            </button>
          ))}
        </div>

        {/* 期間プリセット */}
        <div className="flex items-center gap-1 rounded-lg border border-white/8 bg-white/3 p-0.5">
          {PERIODS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setPeriod(value)}
              className={cn(
                "rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                period === value
                  ? "bg-white/10 text-white"
                  : "text-slate-500 hover:text-white",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 日付範囲 */}
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-slate-300 outline-none focus:border-brand-500"
          />
          <span className="text-slate-600 text-xs">〜</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-white/10 bg-slate-800 px-2 py-1.5 text-xs text-slate-300 outline-none focus:border-brand-500"
          />
        </div>

        {/* 大会 */}
        <select
          value={tournamentId}
          onChange={(e) => setTournamentId(e.target.value)}
          className="rounded-lg border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 outline-none focus:border-brand-500"
        >
          <option value="">全大会</option>
          {filteredTournaments.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>

        {/* リセット */}
        <button
          onClick={reset}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-500 hover:text-white transition-colors"
        >
          <RotateCcw className="h-3 w-3" />
          リセット
        </button>
      </div>
    </div>
  );
}
