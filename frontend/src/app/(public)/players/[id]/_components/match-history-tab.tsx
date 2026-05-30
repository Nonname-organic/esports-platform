"use client";

import { useState } from "react";
import Link from "next/link";
import { Swords, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { usePlayerMatchHistory } from "@/features/players/hooks/use-player";
import { cn } from "@/lib/utils";
import type { PlayerMatchHistory } from "@/types/player";

interface MatchHistoryTabProps {
  playerId: string;
}

export function MatchHistoryTab({ playerId }: MatchHistoryTabProps) {
  const [cursors, setCursors] = useState<(string | undefined)[]>([undefined]);
  const [pageIdx, setPageIdx] = useState(0);

  const { data, isLoading, isError, isFetching } = usePlayerMatchHistory(
    playerId,
    cursors[pageIdx],
  );

  const handleNext = () => {
    if (data?.meta.has_next && data.meta.cursor) {
      setCursors((c) => [...c.slice(0, pageIdx + 1), data.meta.cursor!]);
      setPageIdx((i) => i + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handlePrev = () => {
    if (pageIdx > 0) {
      setPageIdx((i) => i - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2 pt-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-white/5" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-16 text-center text-slate-400 pt-6">
        試合履歴の読み込みに失敗しました
      </div>
    );
  }

  const matches = data?.data ?? [];

  if (matches.length === 0 && pageIdx === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Swords className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">試合履歴がありません</p>
      </div>
    );
  }

  return (
    <div className="pt-6">
      {/* テーブルヘッダー */}
      <div className="mb-2 hidden grid-cols-[auto_1fr_auto_auto_auto_auto_auto] items-center gap-4 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 sm:grid">
        <span>結果</span>
        <span>対戦</span>
        <span>エージェント</span>
        <span>MAP</span>
        <span className="text-center">K/D/A</span>
        <span className="text-center">KDA</span>
        <span />
      </div>

      <div className={cn("space-y-1.5", isFetching && "opacity-60 transition-opacity")}>
        {matches.map((match) => (
          <MatchRow key={match.id} match={match} />
        ))}
      </div>

      {/* ページネーション */}
      {(pageIdx > 0 || data?.meta.has_next) && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            onClick={handlePrev}
            disabled={pageIdx === 0 || isFetching}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            前へ
          </button>
          <span className="text-xs text-slate-600">{pageIdx + 1} ページ目</span>
          <button
            onClick={handleNext}
            disabled={!data?.meta.has_next || isFetching}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
          >
            次へ
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

function MatchRow({ match }: { match: PlayerMatchHistory }) {
  const isWin = match.result === "win";
  const isLoss = match.result === "loss";

  return (
    <div
      className={cn(
        "grid grid-cols-[auto_1fr] items-center gap-3 rounded-xl border bg-slate-900 px-4 py-3 sm:grid-cols-[auto_1fr_auto_auto_auto_auto_auto]",
        isWin && "border-green-500/15",
        isLoss && "border-red-500/10",
        !isWin && !isLoss && "border-white/8",
      )}
    >
      {/* 結果 */}
      <div
        className={cn(
          "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-sm font-black",
          isWin && "bg-green-500/10 text-green-400",
          isLoss && "bg-red-500/10 text-red-400",
          !isWin && !isLoss && "bg-white/5 text-slate-500",
        )}
      >
        {isWin ? "W" : isLoss ? "L" : "–"}
      </div>

      {/* 対戦情報 */}
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-white">
          {match.my_team_name ?? "—"}
          <span className="mx-1.5 text-slate-600">vs</span>
          {match.opponent_team_name ?? "TBD"}
        </p>
        <p className="truncate text-xs text-slate-500">{match.tournament_name}</p>
      </div>

      {/* エージェント */}
      <div className="hidden sm:block flex-shrink-0">
        {match.agent ? (
          <span className="rounded-lg bg-white/5 px-2 py-1 text-xs font-medium text-slate-300">
            {match.agent}
          </span>
        ) : (
          <span className="text-xs text-slate-600">—</span>
        )}
      </div>

      {/* MAP */}
      <div className="hidden sm:block flex-shrink-0 text-xs text-slate-500">
        {match.map_name ?? "—"}
      </div>

      {/* K/D/A */}
      <div className="hidden sm:block flex-shrink-0 text-center tabular-nums text-sm">
        <span className="text-green-400">{match.kills}</span>
        <span className="text-slate-600">/</span>
        <span className="text-red-400">{match.deaths}</span>
        <span className="text-slate-600">/</span>
        <span className="text-yellow-400">{match.assists}</span>
      </div>

      {/* KDA */}
      <div className="hidden sm:block flex-shrink-0 text-center">
        <span
          className={cn(
            "text-sm font-bold tabular-nums",
            match.kda >= 3
              ? "text-green-400"
              : match.kda >= 1.5
              ? "text-white"
              : "text-red-400",
          )}
        >
          {match.kda.toFixed(2)}
        </span>
      </div>

      {/* リンク */}
      <Link
        href={`/matches/${match.match_id}`}
        className="flex-shrink-0 rounded-lg border border-white/10 p-1.5 text-slate-500 hover:text-white transition-colors"
        aria-label="試合詳細"
      >
        <ExternalLink className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
