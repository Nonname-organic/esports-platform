"use client";

import { useState } from "react";
import Link from "next/link";
import { Trophy, Crown, Loader2, Medal } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import { useGlobalRankings } from "@/features/rankings/hooks/use-rankings";
import type { SeasonScope } from "@/features/rankings/api/ranking-api";
import { RankBadge } from "@/components/rank-badge";

const GAMES = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];

export function RankingsClient() {
  const [game, setGame] = useState<string | undefined>(undefined);
  const [season, setSeason] = useState<SeasonScope>("all");
  const { data: board, isLoading } = useGlobalRankings({ game, season, limit: 50 });

  const rows = board ?? [];
  const podium = rows.slice(0, 3);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* ヘッダー */}
      <div className="mb-8 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-brand-400">Competitive</p>
        <h1 className="mt-1 text-4xl font-black tracking-tight text-white sm:text-5xl">RANKINGS</h1>
        <p className="mt-2 text-sm text-slate-400">大会成績から算出したチームの実力ランキング。頂点を目指せ。</p>
      </div>

      {/* フィルタ */}
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
          {/* 表彰台 */}
          {podium.length >= 3 && (
            <div className="mb-8 grid grid-cols-3 items-end gap-3">
              <PodiumCard e={podium[1]} place={2} />
              <PodiumCard e={podium[0]} place={1} />
              <PodiumCard e={podium[2]} place={3} />
            </div>
          )}

          {/* テーブル */}
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
            <div className="hidden grid-cols-[3rem_1fr_9rem_5rem_5rem_5rem] gap-3 border-b border-white/10 px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-500 sm:grid">
              <span>#</span><span>チーム</span><span>Tier</span><span className="text-right">RP</span><span className="text-right">優勝</span><span className="text-right">勝率</span>
            </div>
            <ul className="divide-y divide-white/5">
              {rows.map((e) => {
                const wr = (e.win_rate * 100).toFixed(0);
                return (
                  <li key={e.team_id}>
                    <Link
                      href={`/teams/${e.team_id}`}
                      className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 px-4 py-3 transition-colors hover:bg-white/[0.03] sm:grid-cols-[3rem_1fr_9rem_5rem_5rem_5rem]"
                    >
                      <span className={cn("text-lg font-black tabular-nums", e.rank <= 3 ? "text-yellow-400" : "text-slate-500")}>
                        {e.rank}
                      </span>
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
                      <span className="hidden text-right font-black tabular-nums text-white sm:block">{e.rp.toLocaleString()}</span>
                      <span className="hidden text-right tabular-nums text-slate-300 sm:block">{e.championships}</span>
                      <span className="hidden text-right tabular-nums text-slate-300 sm:block">{wr}%</span>
                      {/* mobile: RP + tier */}
                      <span className="flex flex-col items-end gap-1 sm:hidden">
                        <RankBadge tierKey={e.tier_key} label={e.tier_label} color={e.tier_color} size="sm" />
                        <span className="text-xs font-black text-white">{e.rp.toLocaleString()} RP</span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        </>
      )}
    </div>
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

function PodiumCard({ e, place }: { e: { team_id: string; team_name: string; team_tag: string; team_logo_url: string | null; rp: number; tier_label: string; tier_color: string; tier_key: string }; place: number }) {
  const ring = place === 1 ? "border-yellow-400/50 shadow-[0_0_40px_-12px_rgba(234,179,8,0.6)]" : place === 2 ? "border-slate-300/40" : "border-amber-700/40";
  const Icon = place === 1 ? Crown : Medal;
  const iconColor = place === 1 ? "text-yellow-400" : place === 2 ? "text-slate-300" : "text-amber-600";
  return (
    <Link
      href={`/teams/${e.team_id}`}
      className={cn(
        "group flex flex-col items-center rounded-2xl border bg-slate-900 p-4 text-center transition-transform hover:-translate-y-1",
        ring,
        place === 1 ? "pb-6" : "mt-4",
      )}
    >
      <Icon className={cn("mb-1 h-6 w-6", iconColor)} />
      <span className="mb-2 flex h-14 w-14 items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-slate-800">
        {e.team_logo_url ? <img src={e.team_logo_url} alt="" className="h-full w-full object-contain" /> : <span className="text-sm font-black text-slate-500">{e.team_tag.slice(0, 2)}</span>}
      </span>
      <p className="line-clamp-1 text-sm font-black text-white">{e.team_name}</p>
      <p className="mt-1 text-lg font-black tabular-nums text-white">{e.rp.toLocaleString()}<span className="ml-0.5 text-[10px] font-bold text-slate-500">RP</span></p>
      <span className="mt-1"><RankBadge tierKey={e.tier_key} label={e.tier_label} color={e.tier_color} size="sm" /></span>
    </Link>
  );
}
