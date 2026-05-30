"use client";

import { useState } from "react";
import Link from "next/link";
import { Swords, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { useTeamMatches } from "@/features/teams/hooks/use-teams";
import { cn, formatDate } from "@/lib/utils";
import type { TeamMatchSummary } from "@/types/team";

interface MatchesTabProps {
  teamId: string;
}

export function MatchesTab({ teamId }: MatchesTabProps) {
  const [cursors, setCursors] = useState<(string | undefined)[]>([undefined]);
  const [pageIdx, setPageIdx] = useState(0);

  const { data, isLoading, isError, isFetching } = useTeamMatches(teamId, cursors[pageIdx]);

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
          <div key={i} className="h-20 animate-pulse rounded-xl bg-white/5" />
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
      <div className={cn("space-y-2", isFetching && "opacity-60 transition-opacity")}>
        {matches.map((match) => (
          <TeamMatchCard key={match.id} match={match} teamId={teamId} />
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

function TeamMatchCard({ match, teamId }: { match: TeamMatchSummary; teamId: string }) {
  const isWin = match.result === "win";
  const isLoss = match.result === "loss";
  const isPending = match.result == null;

  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-xl border bg-slate-900 px-4 py-3",
        isWin && "border-green-500/20",
        isLoss && "border-red-500/15",
        isPending && "border-white/8",
      )}
    >
      {/* 結果バッジ */}
      <div
        className={cn(
          "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg text-sm font-black",
          isWin && "bg-green-500/10 text-green-400",
          isLoss && "bg-red-500/10 text-red-400",
          isPending && "bg-white/5 text-slate-500",
        )}
      >
        {isWin ? "W" : isLoss ? "L" : "–"}
      </div>

      {/* 対戦相手 */}
      <div className="flex flex-1 items-center gap-3 min-w-0">
        <div className="h-8 w-8 flex-shrink-0 overflow-hidden rounded-lg border border-white/10 bg-slate-800 flex items-center justify-center">
          {match.opponent?.logo_url ? (
            <img src={match.opponent.logo_url} alt={match.opponent.name} className="h-full w-full object-contain" />
          ) : (
            <span className="text-[10px] font-bold text-slate-500">
              {match.opponent?.tag?.slice(0, 3) ?? "TBD"}
            </span>
          )}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">
            {match.opponent?.name ?? "TBD"}
          </p>
          <p className="text-xs text-slate-500">{match.tournament_name}</p>
        </div>
      </div>

      {/* スコア */}
      <div className="flex-shrink-0 text-center">
        <p className={cn(
          "text-lg font-black",
          isWin ? "text-green-400" : isLoss ? "text-red-400" : "text-slate-500",
        )}>
          {match.team_score} – {match.opponent_score}
        </p>
        <p className="text-[10px] text-slate-600">{match.format}</p>
      </div>

      {/* 日時 */}
      {match.played_at && (
        <div className="hidden sm:block flex-shrink-0 text-right">
          <p className="text-xs text-slate-500">
            {new Date(match.played_at).toLocaleDateString("ja-JP", {
              month: "numeric",
              day: "numeric",
            })}
          </p>
        </div>
      )}

      {/* リンク */}
      <Link
        href={`/matches/${match.id}`}
        className="flex-shrink-0 rounded-lg border border-white/10 p-1.5 text-slate-500 hover:text-white transition-colors"
        aria-label="試合詳細"
      >
        <ExternalLink className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
