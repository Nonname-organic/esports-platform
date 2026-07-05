"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, PlaneTakeoff } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn, getGameColor, formatPrize } from "@/lib/utils";
import type { ListResponse, TournamentSummary } from "@/types/tournament";
import { Countdown } from "@/components/live/countdown";
import { LiveDot } from "@/components/live/live-dot";

function startShort(iso: string | null): string {
  if (!iso) return "TBD";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "TBD" : d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/**
 * 受付中で「最も締切が近い」大会 = Hero の受付カウンター。
 * 空港の搭乗ゲート / ディパーチャーボードを模した実データ表示（捏造なし）。
 */
export function FeaturedEntry() {
  const { data, isLoading } = useQuery({
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

  const t = (data ?? [])
    .slice()
    .sort((a, b) => {
      const ta = a.registration_end_at ? new Date(a.registration_end_at).getTime() : Infinity;
      const tb = b.registration_end_at ? new Date(b.registration_end_at).getTime() : Infinity;
      return ta - tb;
    })[0];

  if (isLoading && !t) {
    return <div className="mt-10 h-[236px] w-full max-w-2xl animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />;
  }
  if (!t) return null;

  return (
    <Link
      href={`/tournaments/${t.id}`}
      className={cn(
        "group mt-10 block w-full max-w-2xl overflow-hidden rounded-2xl border border-green-500/30 bg-slate-950/80 backdrop-blur-md",
        "shadow-[0_0_50px_-14px_rgba(34,197,94,0.55)] transition-all duration-300 hover:-translate-y-0.5 hover:border-green-400/60 hover:shadow-[0_0_60px_-8px_rgba(34,197,94,0.75)]",
      )}
    >
      {/* ゲート帯 */}
      <div className="flex items-center gap-2 border-b border-white/10 bg-green-500/10 px-4 py-1.5 font-mono">
        <LiveDot />
        <span className="text-[11px] font-black tracking-[0.25em] text-green-400">ENTRY OPEN</span>
        <span className="hidden text-[10px] tracking-widest text-slate-500 sm:inline">· RECEPTION GATE</span>
        <span className={cn("ml-auto rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(t.game))}>
          {t.game}
        </span>
      </div>

      <div className="px-5 py-4 text-left">
        {/* 便名 = 大会名 */}
        <p className="flex items-center gap-1.5 font-mono text-[10px] font-bold tracking-[0.3em] text-slate-500">
          <PlaneTakeoff className="h-3 w-3" /> NOW BOARDING
        </p>
        <h2 className="mt-0.5 truncate text-xl font-black tracking-tight text-white transition-colors group-hover:text-green-300 sm:text-2xl">
          {t.name}
        </h2>

        {/* ディパーチャーボード行 */}
        <div className="mt-3 grid grid-cols-2 gap-2 font-mono sm:grid-cols-4">
          <BoardCell label="TEAMS" value={String(t.max_teams)} />
          <BoardCell label="REGISTERED" value={`${t.registered_teams}/${t.max_teams}`} accent />
          <BoardCell label="PRIZE" value={t.prize_pool && t.prize_pool > 0 ? formatPrize(t.prize_pool) : "—"} />
          <BoardCell label="STARTS" value={startShort(t.start_at)} />
        </div>

        {/* カウントダウンボード + CTA */}
        <div className="mt-4 flex flex-wrap items-end justify-between gap-3 rounded-xl border border-white/10 bg-black/40 px-4 py-3">
          <div>
            <p className="mb-1 font-mono text-[10px] font-bold tracking-[0.3em] text-slate-500">ENTRY CLOSES IN</p>
            <Countdown target={t.registration_end_at} size="lg" />
          </div>
          <span className="inline-flex items-center gap-1 rounded-lg bg-green-500 px-5 py-2.5 text-sm font-black text-white transition-transform group-hover:translate-x-0.5">
            エントリーする
            <ChevronRight className="h-4 w-4" />
          </span>
        </div>
      </div>
    </Link>
  );
}

function BoardCell({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg border border-white/8 bg-white/[0.03] px-2.5 py-1.5">
      <p className="text-[9px] font-bold tracking-widest text-slate-500">{label}</p>
      <p className={cn("truncate text-sm font-black tabular-nums", accent ? "text-green-300 animate-board-flicker" : "text-white")}>
        {value}
      </p>
    </div>
  );
}
