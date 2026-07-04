"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Users, ChevronRight, Trophy } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
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
    <section>
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tournaments.map((t) => (
          <LiveTournamentCard key={t.id} t={t} />
        ))}
      </div>
    </section>
  );
}

function LiveTournamentCard({ t }: { t: TournamentSummary }) {
  const fill = Math.min((t.registered_teams / Math.max(t.max_teams, 1)) * 100, 100);

  return (
    <Link
      href={`/tournaments/${t.id}`}
      className={cn(
        "group relative block overflow-hidden rounded-2xl border border-white/10 bg-slate-900",
        "transition-all duration-300 will-change-transform",
        "hover:-translate-y-1 hover:border-green-500/50 hover:shadow-[0_10px_40px_-10px_rgba(34,197,94,0.35)]",
      )}
    >
      {/* バナー（Hover時 Zoom） */}
      <div className="relative h-36 overflow-hidden bg-gradient-to-br from-slate-800 to-slate-950">
        {t.banner_url ? (
          <img
            src={t.banner_url}
            alt=""
            className="h-full w-full object-cover opacity-55 transition-transform duration-500 group-hover:scale-110 group-hover:opacity-75"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <Trophy className="h-12 w-12 text-white/10" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/30 to-transparent" />

        {/* ゲーム + LIVE */}
        <span className={cn("absolute left-3 top-3 rounded-full border px-2.5 py-0.5 text-[11px] font-bold", getGameColor(t.game))}>
          {t.game}
        </span>
        <span className="absolute right-3 top-3">
          <LiveBadge />
        </span>

        {/* 賞金 */}
        {t.prize_pool != null && t.prize_pool > 0 && (
          <span className="absolute bottom-3 right-3 rounded-lg bg-black/50 px-2 py-1 text-xs font-bold text-yellow-400 backdrop-blur-sm">
            {formatPrize(t.prize_pool)}
          </span>
        )}
      </div>

      {/* 本文 */}
      <div className="p-4">
        <h3 className="line-clamp-1 font-bold text-white transition-colors group-hover:text-green-400">
          {t.name}
        </h3>

        <div className="mt-2 flex items-center gap-2 text-sm text-slate-400">
          <Users className="h-3.5 w-3.5 text-slate-500" />
          <span className="font-semibold text-white">{t.registered_teams}</span>
          <span className="text-slate-500">/ {t.max_teams} Teams</span>
        </div>

        {/* 参加率バー */}
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
            <span>参加状況</span>
            <span className="tabular-nums">{fill.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-brand-500 to-green-400 transition-all duration-500"
              style={{ width: `${fill}%` }}
            />
          </div>
        </div>
      </div>
    </Link>
  );
}
