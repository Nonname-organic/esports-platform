"use client";

import { useState } from "react";
import Link from "next/link";
import { Trophy, Crown, Loader2, Medal } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import { useGlobalRankings } from "@/features/rankings/hooks/use-rankings";
import type { LeaderboardEntry, SeasonScope } from "@/features/rankings/api/ranking-api";
import { RankBadge } from "@/components/rank-badge";
import { AnimatedNumber } from "@/components/live/animated-number";

const GAMES = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];

export function RankingsClient() {
  const [game, setGame] = useState<string | undefined>(undefined);
  const [season, setSeason] = useState<SeasonScope>("all");
  const { data: board, isLoading } = useGlobalRankings({ game, season, limit: 50 });

  const rows = board ?? [];
  const podium = rows.slice(0, 3);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* Hero */}
      <div className="mb-8 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-brand-400">Competitive</p>
        <h1 className="mt-1 text-4xl font-black tracking-tight text-white sm:text-5xl">RANKINGS</h1>
        <p className="mt-2 text-sm text-slate-400">大会成績から算出したチームの実力ランキング。頂点を目指せ。</p>
      </div>

      {/* Filters */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex flex-wrap justify-center gap-2">
          <FilterPill active={!game} onClick={() => setGame(undefined)}>All Games</FilterPill>
          {GAMES.map((g) => (
            <FilterPill key={g} active={game === g} onClick={() => setGame(g)}>{g}</FilterPill>
          ))}
        </div>
        <div className="inline-flex rounded-full border border-white/10 bg-white/5 p-1">
          {(["all", "current"] as SeasonScope[]).map((s) => (
            <button
              key={s}
              onClick={() => setSeason(s)}
              className={cn(
                "rounded-full px-4 py-1.5 text-xs font-bold transition-colors",
                season === s ? "bg-brand-500 text-white" : "text-slate-400 hover:text-white",
              )}
            >
              {s === "all" ? "全期間" : "今シーズン"}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
        </div>
      ) : rows.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center rounded-2xl border border-white/10 bg-slate-900 text-center">
          <Trophy className="mb-3 h-10 w-10 text-slate-700" />
          <p className="text-sm text-slate-500">まだランキングデータがありません。</p>
          <p className="text-xs text-slate-600">大会が完了するとここに反映されます。</p>
        </div>
      ) : (
        <>
          {/* Top3 Podium */}
          {podium.length >= 3 && (
            <div className="mb-8 grid grid-cols-3 items-end gap-3">
              <PodiumCard e={podium[1]} place={2} />
              <PodiumCard e={podium[0]} place={1} />
              <PodiumCard e={podium[2]} place={3} />
            </div>
          )}

          {/* Leaderboard */}
          <div className="hidden grid-cols-[3rem_1fr_9rem_6rem_4rem_4rem] gap-3 px-4 pb-1 text-[11px] font-bold uppercase tracking-wider text-slate-500 sm:grid">
            <span>順位</span><span>チーム</span><span>Tier</span><span className="text-right">RP</span><span className="text-right">優勝</span><span className="text-right">勝率</span>
          </div>
          <ul className="space-y-1.5">
            {rows.map((e) => (
              <LeaderboardRow key={e.team_id} e={e} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function LeaderboardRow({ e }: { e: LeaderboardEntry }) {
  const wr = (e.win_rate * 100).toFixed(0);
  return (
    <li className="relative overflow-hidden rounded-xl">
      {/* Tier アクセント（左） */}
      <span className="absolute inset-y-0 left-0 w-1 opacity-60" style={{ backgroundColor: e.tier_color }} aria-hidden />
      <Link
        href={`/teams/${e.team_id}`}
        className={cn(
          "grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 border border-white/8 bg-slate-900 px-4 py-3 pl-5",
          "transition-all duration-200 will-change-transform hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.04] hover:shadow-[0_10px_30px_-12px_rgba(0,0,0,0.6)]",
          "sm:grid-cols-[3rem_1fr_9rem_6rem_4rem_4rem]",
        )}
      >
        <span className={cn("text-lg font-black tabular-nums", e.rank <= 3 ? "text-yellow-400" : "text-slate-500")}>{e.rank}</span>
        <span className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-800">
            {e.team_logo_url ? <img src={e.team_logo_url} alt="" className="h-full w-full object-contain" /> : <span className="text-[10px] text-slate-500">{e.team_tag.slice(0, 2)}</span>}
          </span>
          <span className="min-w-0">
            <span className="block truncate font-bold text-white">{e.team_name}</span>
            <span className={cn("inline-block rounded px-1 text-[10px] font-bold", getGameColor(e.game))}>{e.game}</span>
          </span>
        </span>
        <span className="hidden sm:block"><RankBadge tierKey={e.tier_key} label={e.tier_label} color={e.tier_color} size="sm" /></span>
        <span className="hidden text-right font-black tabular-nums text-white sm:block"><AnimatedNumber value={e.rp} durationMs={900} /></span>
        <span className="hidden text-right tabular-nums text-slate-300 sm:block">{e.championships}</span>
        <span className="hidden text-right tabular-nums text-slate-300 sm:block">{wr}%</span>
        {/* mobile */}
        <span className="flex flex-col items-end gap-1 sm:hidden">
          <RankBadge tierKey={e.tier_key} label={e.tier_label} color={e.tier_color} size="sm" />
          <span className="text-xs font-black text-white"><AnimatedNumber value={e.rp} durationMs={900} /> RP</span>
        </span>
      </Link>
    </li>
  );
}

function FilterPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full border px-3.5 py-1.5 text-xs font-bold transition-colors",
        active ? "border-brand-500/50 bg-brand-500/15 text-brand-300" : "border-white/10 text-slate-400 hover:text-white",
      )}
    >
      {children}
    </button>
  );
}

function PodiumCard({ e, place }: { e: LeaderboardEntry; place: number }) {
  const Icon = place === 1 ? Crown : Medal;
  const iconColor = place === 1 ? "text-yellow-400" : place === 2 ? "text-slate-300" : "text-amber-600";
  return (
    <Link
      href={`/teams/${e.team_id}`}
      className={cn(
        "group flex flex-col items-center rounded-2xl border bg-slate-900 p-4 text-center transition-transform hover:-translate-y-1",
        place === 1 ? "pb-6" : "mt-4",
      )}
      style={{
        borderColor: `${e.tier_color}55`,
        boxShadow: place === 1 ? `0 0 44px -14px ${e.tier_color}` : undefined,
      }}
    >
      <Icon className={cn("mb-2 h-6 w-6", iconColor)} />
      {/* Tier リング + Progress + Glow */}
      <RankBadge variant="ring" tierKey={e.tier_key} label={e.tier_label} color={e.tier_color} progress={e.progress} size={place === 1 ? "lg" : "md"} />
      <span className="mt-2 flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-800">
        {e.team_logo_url ? <img src={e.team_logo_url} alt="" className="h-full w-full object-contain" /> : <span className="text-[11px] font-black text-slate-500">{e.team_tag.slice(0, 2)}</span>}
      </span>
      <p className="mt-1 line-clamp-1 text-sm font-black text-white">{e.team_name}</p>
      <p className="text-lg font-black tabular-nums text-white">
        <AnimatedNumber value={e.rp} durationMs={1100} /><span className="ml-0.5 text-[10px] font-bold text-slate-500">RP</span>
      </p>
    </Link>
  );
}
