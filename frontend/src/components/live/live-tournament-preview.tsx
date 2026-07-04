"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Trophy, Users, ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor } from "@/lib/utils";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { LiveBadge } from "./live-dot";

export function LiveTournamentPreview({ initial }: { initial: TournamentSummary[] }) {
  // 60秒ごとに再取得。タブ非表示中は自動停止（refetchIntervalInBackground: false）。
  const { data } = useQuery({
    queryKey: ["live", "ongoing-tournaments"],
    queryFn: async () => {
      const res = await apiClient.get<ListResponse<TournamentSummary>>(
        "/api/v1/tournaments?status=ongoing&limit=3",
      );
      return res.data;
    },
    initialData: initial,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });

  const tournaments = (data ?? []).slice(0, 3);
  if (tournaments.length === 0) return null;

  return (
    <section className="mb-12">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-bold text-white">
          <span className="text-green-400">開催中</span>の大会
          <LiveBadge />
        </h2>
        <Link
          href="/tournaments?status=ongoing"
          className="flex items-center gap-1 text-sm text-brand-400 hover:text-brand-300 transition-colors"
        >
          すべて見る
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {tournaments.map((t) => (
          <Link
            key={t.id}
            href={`/tournaments/${t.id}`}
            className="group relative overflow-hidden rounded-xl border border-white/10 bg-slate-900 p-4 transition-all hover:border-green-500/40 hover:shadow-lg hover:shadow-green-500/5"
          >
            {/* LIVE バッジ（右上・ゆっくり点滅） */}
            <span className="absolute right-3 top-3">
              <LiveBadge />
            </span>

            <span className={cn("inline-block rounded-full border px-2 py-0.5 text-[11px] font-bold", getGameColor(t.game))}>
              {t.game}
            </span>
            <h3 className="mt-2 line-clamp-2 pr-16 font-bold text-white transition-colors group-hover:text-green-400">
              {t.name}
            </h3>
            <div className="mt-3 flex items-center gap-2 text-sm text-slate-400">
              <Users className="h-3.5 w-3.5 text-slate-500" />
              <span className="font-semibold text-white">{t.registered_teams}</span>
              <span className="text-slate-500">/ {t.max_teams} Teams</span>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
              <Trophy className="h-3 w-3" />
              開催中
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
