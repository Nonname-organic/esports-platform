"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Trophy, Star, ChevronRight } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import { liveApi } from "@/features/live/api/live-api";

/** 直近優勝チームのハイライト（勝者＝目指す姿を見せて参加意欲を高める）。 */
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

  return (
    <section>
      <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
        <Trophy className="h-5 w-5 text-yellow-400" />
        直近の<span className="text-yellow-400">王者</span>
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {champions.map((c) => (
          <Link
            key={c.tournament_id}
            href={`/tournaments/${c.tournament_id}`}
            className={cn(
              "group relative overflow-hidden rounded-2xl border border-yellow-500/20 bg-gradient-to-br from-slate-900 to-slate-950 p-5",
              "transition-all duration-300 hover:-translate-y-1 hover:border-yellow-400/50 hover:shadow-[0_12px_40px_-12px_rgba(234,179,8,0.4)]",
            )}
          >
            {/* 背景グロー */}
            <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-yellow-500/10 blur-2xl transition-opacity group-hover:opacity-100 opacity-60" />

            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-yellow-500/15 px-2.5 py-0.5 text-[11px] font-black tracking-wide text-yellow-400">
                <Trophy className="h-3 w-3" /> CHAMPION
              </span>
              <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(c.game))}>
                {c.game}
              </span>
            </div>

            <p className="mt-3 text-xl font-black text-white transition-colors group-hover:text-yellow-300">
              {c.champion_team_name ?? "—"}
            </p>
            <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{c.tournament_name}</p>

            {c.mvp_name && (
              <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-slate-400">
                <Star className="h-3.5 w-3.5 text-pink-400" />
                MVP <span className="font-semibold text-white">{c.mvp_name}</span>
              </p>
            )}

            <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-yellow-400/80 transition-transform group-hover:translate-x-0.5">
              大会を見る <ChevronRight className="h-3.5 w-3.5" />
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
