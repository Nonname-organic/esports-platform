"use client";

import { useState } from "react";
import Link from "next/link";
import { Trophy, Crown, Loader2, Medal } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import { useGlobalRankings, usePlayerRankings } from "@/features/rankings/hooks/use-rankings";
import type { LeaderboardEntry, PlayerLeaderboardEntry, SeasonScope } from "@/features/rankings/api/ranking-api";
import { RankBadge } from "@/components/rank-badge";
import { AnimatedNumber } from "@/components/live/animated-number";

const GAMES = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];
type Scope = "team" | "player";

export function RankingsClient() {
  const [scope, setScope] = useState<Scope>("team");
  const [game, setGame] = useState<string | undefined>(undefined);
  const [season, setSeason] = useState<SeasonScope>("all");

  const team = useGlobalRankings({ game, season, limit: 50 });
  const player = usePlayerRankings({ game, season, limit: 50 });
  const isLoading = scope === "team" ? team.isLoading : player.isLoading;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* Hero */}
      <div className="mb-8 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-brand-400">Competitive</p>
        <h1 className="mt-1 text-4xl font-black tracking-tight text-white sm:text-5xl">RANKINGS</h1>
        <p className="mt-2 text-sm text-slate-400">大会成績から算出した実力ランキング。頂点を目指せ。</p>
      </div>

      {/* Scope + Season */}
      <div className="mb-4 flex flex-wrap items-center justify-center gap-3">
        <Segmented value={scope} onChange={(v) => setScope(v as Scope)} options={[["team", "チーム"], ["player", "プレイヤー"]]} />
        <Segmented value={season} onChange={(v) => setSeason(v as SeasonScope)} options={[["all", "全期間"], ["current", "今季"], ["previous", "前季"]]} />
      </div>

      {/* Game filter */}
      <div className="mb-8 flex flex-wrap justify-center gap-2">
        <FilterPill active={!game} onClick={() => setGame(undefined)}>All Games</FilterPill>
        {GAMES.map((g) => (
          <FilterPill key={g} active={game === g} onClick={() => setGame(g)}>{g}</FilterPill>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-24"><Loader2 className="h-8 w-8 animate-spin text-brand-500" /></div>
      ) : scope === "team" ? (
        <TeamBoard rows={team.data ?? []} />
      ) : (
        <PlayerBoard rows={player.data ?? []} />
      )}
    </div>
  );
}

// ── Team ─────────────────────────────────────────────────────────────────────
function TeamBoard({ rows }: { rows: LeaderboardEntry[] }) {
  if (rows.length === 0) return <Empty />;
  const podium = rows.slice(0, 3);
  return (
    <>
      {podium.length >= 3 && (
        <div className="mb-8 grid grid-cols-3 items-end gap-3">
          <Podium href={`/teams/${podium[1].team_id}`} place={2} tier={tier(podium[1])} progress={podium[1].progress} logo={podium[1].team_logo_url} tag={podium[1].team_tag} name={podium[1].team_name} rp={podium[1].rp} />
          <Podium href={`/teams/${podium[0].team_id}`} place={1} tier={tier(podium[0])} progress={podium[0].progress} logo={podium[0].team_logo_url} tag={podium[0].team_tag} name={podium[0].team_name} rp={podium[0].rp} />
          <Podium href={`/teams/${podium[2].team_id}`} place={3} tier={tier(podium[2])} progress={podium[2].progress} logo={podium[2].team_logo_url} tag={podium[2].team_tag} name={podium[2].team_name} rp={podium[2].rp} />
        </div>
      )}
      <div className="hidden grid-cols-[3rem_1fr_9rem_6rem_4rem_4rem] gap-3 px-4 pb-1 text-[11px] font-bold uppercase tracking-wider text-slate-500 sm:grid">
        <span>順位</span><span>チーム</span><span>Tier</span><span className="text-right">RP</span><span className="text-right">優勝</span><span className="text-right">勝率</span>
      </div>
      <ul className="space-y-1.5">
        {rows.map((e) => (
          <Row key={e.team_id} href={`/teams/${e.team_id}`} rank={e.rank} change={e.rank_change} tier={tier(e)}
            logo={e.team_logo_url} tag={e.team_tag} name={e.team_name} game={e.game} rp={e.rp}
            c1={String(e.championships)} c2={`${(e.win_rate * 100).toFixed(0)}%`} />
        ))}
      </ul>
    </>
  );
}

// ── Player ───────────────────────────────────────────────────────────────────
function PlayerBoard({ rows }: { rows: PlayerLeaderboardEntry[] }) {
  if (rows.length === 0) return <Empty />;
  const podium = rows.slice(0, 3);
  return (
    <>
      {podium.length >= 3 && (
        <div className="mb-8 grid grid-cols-3 items-end gap-3">
          <Podium href={`/players/${podium[1].player_id}`} place={2} tier={tier(podium[1])} progress={podium[1].progress} logo={null} tag={podium[1].in_game_name} name={podium[1].in_game_name} rp={podium[1].rp} />
          <Podium href={`/players/${podium[0].player_id}`} place={1} tier={tier(podium[0])} progress={podium[0].progress} logo={null} tag={podium[0].in_game_name} name={podium[0].in_game_name} rp={podium[0].rp} />
          <Podium href={`/players/${podium[2].player_id}`} place={3} tier={tier(podium[2])} progress={podium[2].progress} logo={null} tag={podium[2].in_game_name} name={podium[2].in_game_name} rp={podium[2].rp} />
        </div>
      )}
      <div className="hidden grid-cols-[3rem_1fr_9rem_6rem_4rem] gap-3 px-4 pb-1 text-[11px] font-bold uppercase tracking-wider text-slate-500 sm:grid">
        <span>順位</span><span>プレイヤー</span><span>Tier</span><span className="text-right">RP</span><span className="text-right">MVP</span>
      </div>
      <ul className="space-y-1.5">
        {rows.map((e) => (
          <Row key={e.player_id} href={`/players/${e.player_id}`} rank={e.rank} change={e.rank_change} tier={tier(e)}
            logo={null} tag={e.in_game_name} name={e.in_game_name} game={e.game} rp={e.rp} c1={`⭐ ${e.mvps}`} narrow />
        ))}
      </ul>
    </>
  );
}

// ── 共通 ─────────────────────────────────────────────────────────────────────
type Tier = { key: string; label: string; color: string };
function tier(e: { tier_key: string; tier_label: string; tier_color: string }): Tier {
  return { key: e.tier_key, label: e.tier_label, color: e.tier_color };
}

/** 前回比の順位変動（▲上昇 / ▼下降 / −変動なし / 未取得は非表示） */
function RankChange({ change }: { change?: number | null }) {
  if (change == null) return null;
  if (change === 0) return <span className="text-[10px] font-bold text-slate-600">−</span>;
  const up = change > 0;
  return (
    <span className={cn("text-[10px] font-black tabular-nums", up ? "text-emerald-400" : "text-red-400")}>
      {up ? "▲" : "▼"}{Math.abs(change)}
    </span>
  );
}

function Row({
  href, rank, change, tier, logo, tag, name, game, rp, c1, c2, narrow,
}: {
  href: string; rank: number; change?: number | null; tier: Tier; logo: string | null; tag: string; name: string; game: string;
  rp: number; c1: string; c2?: string; narrow?: boolean;
}) {
  return (
    <li className="relative overflow-hidden rounded-xl">
      <span className="absolute inset-y-0 left-0 w-1 opacity-60" style={{ backgroundColor: tier.color }} aria-hidden />
      <Link
        href={href}
        className={cn(
          "grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 border border-white/8 bg-slate-900 px-4 py-3 pl-5",
          "transition-all duration-200 will-change-transform hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.04] hover:shadow-[0_10px_30px_-12px_rgba(0,0,0,0.6)]",
          narrow ? "sm:grid-cols-[3rem_1fr_9rem_6rem_4rem]" : "sm:grid-cols-[3rem_1fr_9rem_6rem_4rem_4rem]",
        )}
      >
        <span className="flex flex-col items-start leading-none">
          <span className={cn("text-lg font-black tabular-nums", rank <= 3 ? "text-yellow-400" : "text-slate-500")}>{rank}</span>
          <RankChange change={change} />
        </span>
        <span className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-800">
            {logo ? <img src={logo} alt="" className="h-full w-full object-contain" /> : <span className="text-[10px] text-slate-500">{tag.slice(0, 2)}</span>}
          </span>
          <span className="min-w-0">
            <span className="block truncate font-bold text-white">{name}</span>
            <span className={cn("inline-block rounded px-1 text-[10px] font-bold", getGameColor(game))}>{game}</span>
          </span>
        </span>
        <span className="hidden sm:block"><RankBadge tierKey={tier.key} label={tier.label} color={tier.color} variant="compact" /></span>
        <span className="hidden text-right font-black tabular-nums text-white sm:block"><AnimatedNumber value={rp} durationMs={900} /></span>
        <span className="hidden text-right tabular-nums text-slate-300 sm:block">{c1}</span>
        {c2 != null && <span className="hidden text-right tabular-nums text-slate-300 sm:block">{c2}</span>}
        <span className="flex flex-col items-end gap-1 sm:hidden">
          <RankBadge tierKey={tier.key} label={tier.label} color={tier.color} variant="compact" />
          <span className="text-xs font-black text-white"><AnimatedNumber value={rp} durationMs={900} /> RP</span>
        </span>
      </Link>
    </li>
  );
}

function Podium({
  href, place, tier, progress, logo, tag, name, rp,
}: {
  href: string; place: number; tier: Tier; progress: number; logo: string | null; tag: string; name: string; rp: number;
}) {
  const Icon = place === 1 ? Crown : Medal;
  const iconColor = place === 1 ? "text-yellow-400" : place === 2 ? "text-slate-300" : "text-amber-600";
  return (
    <Link
      href={href}
      className={cn("group flex flex-col items-center rounded-2xl border bg-slate-900 p-4 text-center transition-transform hover:-translate-y-1", place === 1 ? "pb-6" : "mt-4")}
      style={{ borderColor: `${tier.color}55`, boxShadow: place === 1 ? `0 0 44px -14px ${tier.color}` : undefined }}
    >
      <Icon className={cn("mb-2 h-6 w-6", iconColor)} />
      <RankBadge variant="ring" tierKey={tier.key} label={tier.label} color={tier.color} progress={progress} ringLarge={place === 1} pulse={place === 1} />
      <span className="mt-2 flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-800">
        {logo ? <img src={logo} alt="" className="h-full w-full object-contain" /> : <span className="text-[11px] font-black text-slate-500">{tag.slice(0, 2)}</span>}
      </span>
      <p className="mt-1 line-clamp-1 text-sm font-black text-white">{name}</p>
      <p className="text-lg font-black tabular-nums text-white"><AnimatedNumber value={rp} durationMs={1100} /><span className="ml-0.5 text-[10px] font-bold text-slate-500">RP</span></p>
    </Link>
  );
}

function Empty() {
  return (
    <div className="flex h-48 flex-col items-center justify-center rounded-2xl border border-white/10 bg-slate-900 text-center">
      <Trophy className="mb-3 h-10 w-10 text-slate-700" />
      <p className="text-sm text-slate-500">まだランキングデータがありません。</p>
      <p className="text-xs text-slate-600">大会が完了するとここに反映されます。</p>
    </div>
  );
}

function Segmented({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <div className="inline-flex rounded-full border border-white/10 bg-white/5 p-1">
      {options.map(([v, label]) => (
        <button key={v} onClick={() => onChange(v)}
          className={cn("rounded-full px-4 py-1.5 text-xs font-bold transition-colors", value === v ? "bg-brand-500 text-white" : "text-slate-400 hover:text-white")}>
          {label}
        </button>
      ))}
    </div>
  );
}

function FilterPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={cn("rounded-full border px-3.5 py-1.5 text-xs font-bold transition-colors", active ? "border-brand-500/50 bg-brand-500/15 text-brand-300" : "border-white/10 text-slate-400 hover:text-white")}>
      {children}
    </button>
  );
}
