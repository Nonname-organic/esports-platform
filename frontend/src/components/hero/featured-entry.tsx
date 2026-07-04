"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Clock, Users, Coins, ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { deadlineLabel } from "@/features/live/lib/format";
import { LiveDot } from "@/components/live/live-dot";

/** 受付中で「最も締切が近い」大会を Hero 直下に表示（受付会場のメインカウンター）。 */
export function FeaturedEntry() {
  const { data } = useQuery({
    queryKey: ["live", "entry-open"],
    queryFn: async () => {
      const res = await apiClient.get<ListResponse<TournamentSummary>>(
        "/api/v1/tournaments?status=registration_open&limit=12",
      );
      return res.data;
    },
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });

  const featured = (data ?? [])
    .slice()
    .sort((a, b) => {
      const ta = a.registration_end_at ? new Date(a.registration_end_at).getTime() : Infinity;
      const tb = b.registration_end_at ? new Date(b.registration_end_at).getTime() : Infinity;
      return ta - tb;
    })[0];

  if (!featured) return null;
  const dl = deadlineLabel(featured.registration_end_at);

  return (
    <Link
      href={`/tournaments/${featured.id}`}
      className={cn(
        "group mt-10 block w-full max-w-2xl overflow-hidden rounded-2xl border border-green-500/30 bg-slate-950/60 backdrop-blur-md",
        "shadow-[0_0_40px_-12px_rgba(34,197,94,0.5)] transition-all duration-300 hover:-translate-y-0.5 hover:border-green-400/60 hover:shadow-[0_0_50px_-8px_rgba(34,197,94,0.7)]",
      )}
    >
      {/* 上段: ENTRY OPEN */}
      <div className="flex items-center gap-2 border-b border-white/10 bg-green-500/10 px-4 py-1.5">
        <LiveDot />
        <span className="text-[11px] font-black tracking-widest text-green-400">ENTRY OPEN</span>
        <span className={cn("ml-auto rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(featured.game))}>
          {featured.game}
        </span>
      </div>

      {/* 下段: 大会名 + 情報 */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 text-left">
        <span className="min-w-0 flex-1 truncate text-base font-black text-white transition-colors group-hover:text-green-300 sm:text-lg">
          {featured.name}
        </span>

        {dl && (
          <span className={cn("inline-flex items-center gap-1 text-sm font-bold", dl.urgent ? "text-red-400 animate-glow-pulse" : "text-yellow-400")}>
            <Clock className="h-3.5 w-3.5" />
            {dl.text}
          </span>
        )}
        <span className="inline-flex items-center gap-1 text-sm text-slate-300">
          <Users className="h-3.5 w-3.5 text-slate-500" />
          <span className="font-bold text-white">{featured.registered_teams}</span>
          <span className="text-slate-500">/{featured.max_teams}</span>
        </span>
        {featured.prize_pool != null && featured.prize_pool > 0 && (
          <span className="inline-flex items-center gap-1 text-sm font-bold text-yellow-400">
            <Coins className="h-3.5 w-3.5" />
            {formatPrize(featured.prize_pool)}
          </span>
        )}

        <span className="inline-flex items-center gap-1 rounded-lg bg-green-500 px-3 py-1.5 text-xs font-bold text-white transition-transform group-hover:translate-x-0.5">
          エントリー
          <ChevronRight className="h-3.5 w-3.5" />
        </span>
      </div>
    </Link>
  );
}
