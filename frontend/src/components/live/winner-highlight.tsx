"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Trophy, Star, Coins, ChevronRight, Swords } from "lucide-react";
import { cn, getGameColor, formatPrize, formatDate } from "@/lib/utils";
import { liveApi, type RecentChampion } from "@/features/live/api/live-api";

/** 直近優勝チームのショーケース（LAST CHAMPION を大きく、続いて2件）。 */
export function WinnerHighlight() {
  const { data } = useQuery({
    queryKey: ["live", "champions"],
    queryFn: async () => (await liveApi.champions(3)).data,
    refetchInterval: 120000,
    refetchIntervalInBackground: false,
    staleTime: 60000,
  });

  const champions = data ?? [];
  if (champions.length === 0) return null;

  const [last, ...rest] = champions;

  return (
    <section>
      <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
        <Trophy className="h-5 w-5 text-yellow-400" />
        <span className="text-yellow-400">LAST CHAMPION</span>
      </h2>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <LastChampionCard c={last} className="lg:col-span-2" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {rest.map((c) => (
            <MiniChampionCard key={c.tournament_id} c={c} />
          ))}
        </div>
      </div>
    </section>
  );
}

function LastChampionCard({ c, className }: { c: RecentChampion; className?: string }) {
  return (
    <Link
      href={`/tournaments/${c.tournament_id}`}
      className={cn(
        "group relative overflow-hidden rounded-3xl border border-yellow-500/25 bg-slate-950",
        "transition-all duration-300 hover:-translate-y-1 hover:border-yellow-400/50 hover:shadow-[0_20px_60px_-20px_rgba(234,179,8,0.5)]",
        className,
      )}
    >
      {/* 背景 */}
      <div className="absolute inset-0">
        {c.banner_url ? (
          <img src={c.banner_url} alt="" className="h-full w-full object-cover opacity-30 transition-transform duration-500 group-hover:scale-105" />
        ) : (
          <div className="h-full w-full bg-gradient-to-br from-slate-900 to-slate-950" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/70 to-slate-950/30" />
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-yellow-500/10 blur-3xl" />
        {/* Shine スイープ（優勝の輝き） */}
        <span className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-white/15 to-transparent animate-shine" />
        <GoldParticles />
      </div>

      <div className="relative flex min-h-[15rem] flex-col justify-between p-6">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-yellow-500/15 px-3 py-1 text-[11px] font-black tracking-widest text-yellow-400">
            <Trophy className="h-3.5 w-3.5" /> CHAMPION
          </span>
          <span className={cn("rounded-full border px-2.5 py-0.5 text-[10px] font-bold", getGameColor(c.game))}>{c.game}</span>
        </div>

        <div>
          <p className="text-4xl font-black text-white drop-shadow transition-colors group-hover:text-yellow-200 sm:text-5xl">
            {c.champion_team_name ?? "—"}
          </p>
          <p className="mt-1 text-sm text-slate-400">{c.tournament_name}</p>
          <p className="mt-1 text-xs font-semibold tracking-wide text-yellow-500/80">頂点に立った王者 — 次に挑むのは、あなたのチームだ。</p>

          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            {c.runner_up_name && (
              <span className="inline-flex items-center gap-1.5 text-slate-400">
                <Swords className="h-3.5 w-3.5 text-slate-500" /> vs <span className="font-semibold text-slate-200">{c.runner_up_name}</span>
              </span>
            )}
            {c.mvp_name && (
              <span className="inline-flex items-center gap-1.5 text-slate-300">
                <Star className="h-3.5 w-3.5 text-pink-400" /> MVP <span className="font-bold text-white">{c.mvp_name}</span>
              </span>
            )}
            {c.prize != null && c.prize > 0 && (
              <span className="inline-flex items-center gap-1.5 font-bold text-yellow-400">
                <Coins className="h-3.5 w-3.5" /> {formatPrize(c.prize, c.prize_currency ?? "JPY")}
              </span>
            )}
            {c.ended_at && <span className="text-xs text-slate-500">{formatDate(c.ended_at)}</span>}
          </div>
        </div>
      </div>
    </Link>
  );
}

// 金色パーティクル（CSSのみ・座標固定でSSR/CSR一致）
const PARTICLES = [
  { left: "10%", delay: "0s", size: 4 },
  { left: "24%", delay: "0.8s", size: 3 },
  { left: "38%", delay: "1.6s", size: 5 },
  { left: "52%", delay: "0.4s", size: 3 },
  { left: "66%", delay: "2.1s", size: 4 },
  { left: "80%", delay: "1.2s", size: 3 },
  { left: "90%", delay: "2.6s", size: 5 },
];
function GoldParticles() {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/3 overflow-hidden" aria-hidden>
      {PARTICLES.map((p, i) => (
        <span
          key={i}
          className="absolute bottom-0 rounded-full bg-yellow-300 animate-gold-float"
          style={{
            left: p.left,
            width: p.size,
            height: p.size,
            animationDelay: p.delay,
            boxShadow: "0 0 6px rgba(253,224,71,0.9)",
          }}
        />
      ))}
    </div>
  );
}

function MiniChampionCard({ c }: { c: RecentChampion }) {
  return (
    <Link
      href={`/tournaments/${c.tournament_id}`}
      className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-900 p-4 transition-all hover:-translate-y-0.5 hover:border-yellow-400/40"
    >
      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-yellow-500/10">
        <Trophy className="h-5 w-5 text-yellow-400" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-black text-white transition-colors group-hover:text-yellow-300">{c.champion_team_name ?? "—"}</p>
        <p className="truncate text-xs text-slate-500">{c.tournament_name}</p>
      </div>
      <ChevronRight className="h-4 w-4 flex-shrink-0 text-slate-600 transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}
