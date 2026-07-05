"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { GitBranch, ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ApiResponse, BracketResponse, ListResponse, TournamentSummary } from "@/types/tournament";
import { LiveBadge } from "./live-dot";

function stageLabel(round: number, last: number): string {
  const d = last - round;
  if (d === 0) return "Final";
  if (d === 1) return "Semi Final";
  if (d === 2) return "Quarter Final";
  return `Round ${round}`;
}

/** 開催中大会のブラケット進行スナップショット（Quarter → Semi → Final ステッパー）。 */
export function LiveBracketSnapshot() {
  const { data: ongoing } = useQuery({
    queryKey: ["live", "ongoing-tournaments"],
    queryFn: async () => (await apiClient.get<ListResponse<TournamentSummary>>("/api/v1/tournaments?status=ongoing&limit=3")).data,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });
  const top = ongoing?.[0];

  const { data: bracket } = useQuery({
    queryKey: ["live", "bracket-snapshot", top?.id],
    queryFn: async () => (await apiClient.get<ApiResponse<BracketResponse>>(`/api/v1/tournaments/${top!.id}/bracket`)).data,
    enabled: !!top?.id,
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
    staleTime: 20000,
  });

  if (!top || !bracket) return null;

  const roundNums = Object.keys(bracket.rounds).map(Number).filter((n) => !Number.isNaN(n)).sort((a, b) => a - b);
  if (roundNums.length === 0) return null;
  const last = roundNums[roundNums.length - 1];

  // 完了 = 全試合に winner。current = 未完了の最初のラウンド。
  const isDone = (r: number) => (bracket.rounds[r] ?? []).every((m) => !!m.winner_id) && (bracket.rounds[r] ?? []).length > 0;
  const current = roundNums.find((r) => !isDone(r)) ?? last;

  // 表示は最後の3ステージ（Quarter/Semi/Final）
  const steps = roundNums.filter((r) => last - r <= 2);

  return (
    <section>
      <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
        <GitBranch className="h-5 w-5 text-red-400" />
        進行中のブラケット
        <LiveBadge />
      </h2>

      <Link
        href={`/tournaments/${top.id}/bracket`}
        className="group block rounded-2xl border border-white/10 bg-slate-900 p-5 transition-all hover:-translate-y-0.5 hover:border-red-500/40"
      >
        <div className="mb-4 flex items-center justify-between">
          <p className="truncate font-bold text-white">{top.name}</p>
          <span className="inline-flex items-center gap-1 text-xs text-red-400">
            観戦する <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </span>
        </div>

        <div className="flex items-center">
          {steps.map((r, i) => {
            const done = isDone(r);
            const active = r === current;
            return (
              <div key={r} className="flex flex-1 items-center">
                <div className="flex flex-col items-center gap-1.5">
                  <span
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full border text-xs font-black",
                      active
                        ? "border-red-500 bg-red-500/20 text-red-300 animate-live-blink"
                        : done
                        ? "border-green-500/50 bg-green-500/15 text-green-400"
                        : "border-white/15 bg-white/5 text-slate-500",
                    )}
                  >
                    {done ? "✓" : i + 1}
                  </span>
                  <span className={cn("text-[10px] font-bold tracking-wide", active ? "text-red-300" : done ? "text-green-400" : "text-slate-500")}>
                    {stageLabel(r, last)}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className={cn("mx-2 h-0.5 flex-1 rounded-full", done ? "bg-green-500/50" : "bg-white/10")} />
                )}
              </div>
            );
          })}
        </div>
      </Link>
    </section>
  );
}
