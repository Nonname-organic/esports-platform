"use client";

import Link from "next/link";
import { Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTournamentLive } from "@/features/tournament-live/hooks/use-tournament-live";
import type { ImmersionMatch } from "@/features/tournament-live/api/tournament-live-api";
import { LiveBadge } from "@/components/live/live-dot";

/** Live Match Ticker: 進行中の試合をライブ表示（30秒更新）。 */
export function LiveTicker({ tournamentId, active }: { tournamentId: string; active: boolean }) {
  const { data } = useTournamentLive(tournamentId, active);
  const live = data?.live_matches ?? [];
  if (live.length === 0) return null;

  return (
    <section>
      <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-white">
        <Swords className="h-5 w-5 text-red-400" />
        <span className="text-red-400">LIVE</span> Matches
        <LiveBadge />
      </h2>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {live.map((m) => <LiveMatchRow key={m.id} m={m} />)}
      </div>
    </section>
  );
}

function LiveMatchRow({ m }: { m: ImmersionMatch }) {
  const t1Lead = m.score1 > m.score2;
  const t2Lead = m.score2 > m.score1;
  return (
    <Link
      href={`/matches/${m.id}`}
      className="group relative block overflow-hidden rounded-2xl border border-red-500/25 bg-slate-900 p-4 transition-all hover:-translate-y-0.5 hover:border-red-500/50 hover:shadow-[0_10px_30px_-12px_rgba(239,68,68,0.5)]"
    >
      <span className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-red-500/10 to-transparent animate-shine" />
      <div className="mb-2 flex items-center justify-between text-[11px]">
        <span className="font-bold uppercase tracking-wider text-red-400">● LIVE · {m.format}</span>
        {m.current_game?.map && <span className="text-slate-500">Map {m.current_game.map}</span>}
      </div>
      <div className="flex items-center justify-between gap-3">
        <TeamSide name={m.team1?.name ?? "TBD"} logo={m.team1?.logo_url ?? null} tag={m.team1?.tag ?? "?"} lead={t1Lead} />
        <div className="flex flex-shrink-0 items-center gap-2">
          <Score n={m.score1} lead={t1Lead} />
          <span className="text-xs font-bold text-slate-600">VS</span>
          <Score n={m.score2} lead={t2Lead} />
        </div>
        <TeamSide name={m.team2?.name ?? "TBD"} logo={m.team2?.logo_url ?? null} tag={m.team2?.tag ?? "?"} lead={t2Lead} right />
      </div>
      {m.current_game && (
        <p className="mt-2 text-center text-[11px] tabular-nums text-slate-500">
          Game {m.current_game.game_number} · <span className="font-bold text-white">{m.current_game.t1_rounds}</span> - <span className="font-bold text-white">{m.current_game.t2_rounds}</span> Rounds
        </p>
      )}
    </Link>
  );
}

function TeamSide({ name, logo, tag, lead, right }: { name: string; logo: string | null; tag: string; lead: boolean; right?: boolean }) {
  return (
    <div className={cn("flex min-w-0 flex-1 items-center gap-2", right && "flex-row-reverse text-right")}>
      <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-800">
        {logo ? <img src={logo} alt="" className="h-full w-full object-contain" /> : <span className="text-[10px] text-slate-500">{tag.slice(0, 2)}</span>}
      </span>
      <span className={cn("truncate text-sm font-bold", lead ? "text-white" : "text-slate-400")}>{name}</span>
    </div>
  );
}

function Score({ n, lead }: { n: number; lead: boolean }) {
  return <span className={cn("min-w-[1.5rem] text-center text-2xl font-black tabular-nums", lead ? "text-white" : "text-slate-500")}>{n}</span>;
}
