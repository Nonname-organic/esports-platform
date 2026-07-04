"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { LiveBadge } from "./live-dot";
import { TournamentLiveCard } from "./tournament-live-card";

/** 「エントリー受付中」の大会（受付会場の主役）。締切が近い順。 */
export function EntryOpenTournaments() {
  const { data } = useQuery({
    queryKey: ["live", "entry-open"], // Hero の FeaturedEntry とキャッシュ共有
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

  const list = (data ?? [])
    .slice()
    .sort((a, b) => {
      const ta = a.registration_end_at ? new Date(a.registration_end_at).getTime() : Infinity;
      const tb = b.registration_end_at ? new Date(b.registration_end_at).getTime() : Infinity;
      return ta - tb;
    })
    .slice(0, 3);

  if (list.length === 0) return null;

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-bold text-white">
          <span className="text-green-400">エントリー受付中</span>
          <LiveBadge label="OPEN" />
        </h2>
        <Link
          href="/tournaments?status=registration_open"
          className="flex items-center gap-1 text-sm text-green-400 hover:text-green-300 transition-colors"
        >
          すべて見る
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((t) => (
          <TournamentLiveCard key={t.id} t={t} mode="entry" />
        ))}
      </div>
    </section>
  );
}
