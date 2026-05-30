"use client";

import Link from "next/link";
import { Swords, Clock, Radio, ExternalLink } from "lucide-react";
import { useTournamentMatches } from "@/features/matches/hooks/use-matches";
import { cn, formatDate } from "@/lib/utils";
import type { MatchSummary, MatchStatus } from "@/types/match";
import type { TournamentDetail, TournamentFormat } from "@/types/tournament";

const STATUS_CONFIG: Record<MatchStatus, { label: string; className: string }> = {
  scheduled: { label: "予定", className: "text-slate-400 bg-slate-400/10" },
  ongoing: { label: "LIVE", className: "text-red-400 bg-red-400/10 animate-pulse" },
  completed: { label: "終了", className: "text-slate-500 bg-slate-500/10" },
  cancelled: { label: "中止", className: "text-gray-600 bg-gray-600/10" },
  forfeit: { label: "没収", className: "text-orange-400 bg-orange-400/10" },
  no_show: { label: "不戦敗", className: "text-orange-400 bg-orange-400/10" },
};

function getRoundLabel(roundNum: number, totalRounds: number, format: TournamentFormat): string {
  if (format === "round_robin" || format === "swiss") return `第 ${roundNum} ラウンド`;
  const fromEnd = totalRounds - roundNum;
  if (fromEnd === 0) return "決勝";
  if (fromEnd === 1) return "準決勝";
  if (fromEnd === 2) return "準々決勝";
  return `Round ${roundNum}`;
}

function estimateTotalRounds(maxTeams: number, format: TournamentFormat): number {
  if (format === "single_elimination") return Math.ceil(Math.log2(maxTeams));
  if (format === "double_elimination") return Math.ceil(Math.log2(maxTeams)) * 2 - 1;
  return maxTeams - 1;
}

interface MatchesTabProps {
  tournamentId: string;
  tournament: TournamentDetail;
}

export function MatchesTab({ tournamentId, tournament }: MatchesTabProps) {
  const { data: matches, isLoading, isError } = useTournamentMatches(tournamentId);
  const totalRounds = estimateTotalRounds(tournament.max_teams, tournament.format);

  if (isLoading) {
    return (
      <div className="space-y-4 pt-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-16 text-center text-slate-400 pt-6">
        試合情報の読み込みに失敗しました
      </div>
    );
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Swords className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">試合がまだありません</p>
        <p className="mt-1 text-sm text-slate-400">ブラケット生成後に試合が表示されます</p>
      </div>
    );
  }

  // ラウンドでグルーピング
  const grouped = matches.reduce<Record<number, MatchSummary[]>>((acc, match) => {
    const r = match.round_number;
    (acc[r] ??= []).push(match);
    return acc;
  }, {});

  const rounds = Object.keys(grouped)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className="space-y-8 pt-6">
      {rounds.map((roundNum) => (
        <section key={roundNum}>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-400">
            <span className="h-px flex-1 bg-white/10" />
            {getRoundLabel(roundNum, totalRounds, tournament.format)}
            <span className="h-px flex-1 bg-white/10" />
          </h2>
          <div className="space-y-2">
            {grouped[roundNum]
              .sort((a, b) => a.match_number - b.match_number)
              .map((match) => (
                <MatchCard key={match.id} match={match} />
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function MatchCard({ match }: { match: MatchSummary }) {
  const status = STATUS_CONFIG[match.status];
  const isCompleted = match.status === "completed";
  const isOngoing = match.status === "ongoing";

  return (
    <div
      className={cn(
        "rounded-xl border bg-slate-900 p-4 transition-all",
        isOngoing && "border-red-500/30 shadow-sm shadow-red-500/10",
        !isOngoing && "border-white/10 hover:border-white/20",
      )}
    >
      <div className="flex items-center gap-4">
        {/* チーム1 */}
        <TeamDisplay
          team={match.team1}
          score={match.team1_wins}
          isWinner={match.winner_id === match.team1?.id}
          isLoser={isCompleted && match.winner_id !== match.team1?.id && !!match.team1}
          align="right"
        />

        {/* 中央: スコア or ステータス */}
        <div className="flex flex-col items-center gap-1 flex-shrink-0 w-24">
          {isCompleted ? (
            <div className="text-xl font-black text-white">
              {match.team1_wins} – {match.team2_wins}
            </div>
          ) : isOngoing ? (
            <div className="flex items-center gap-1 text-red-400">
              <Radio className="h-3 w-3 animate-pulse" />
              <span className="text-sm font-bold">LIVE</span>
            </div>
          ) : (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-semibold",
                status.className,
              )}
            >
              {status.label}
            </span>
          )}
          <span className="text-xs text-slate-600">{match.format}</span>
        </div>

        {/* チーム2 */}
        <TeamDisplay
          team={match.team2}
          score={match.team2_wins}
          isWinner={match.winner_id === match.team2?.id}
          isLoser={isCompleted && match.winner_id !== match.team2?.id && !!match.team2}
          align="left"
        />

        {/* アクション */}
        <div className="ml-auto flex items-center gap-2 flex-shrink-0">
          {match.stream_url && isOngoing && (
            <a
              href={match.stream_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 rounded-lg bg-red-500/10 px-2 py-1 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <Radio className="h-3 w-3" />
              配信
            </a>
          )}
          <Link
            href={`/matches/${match.id}`}
            className="rounded-lg border border-white/10 px-2 py-1 text-xs text-slate-400 hover:border-white/20 hover:text-white transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* スケジュール */}
      {match.scheduled_at && !isCompleted && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
          <Clock className="h-3 w-3" />
          {formatDate(match.scheduled_at)}
        </p>
      )}
      {match.ended_at && isCompleted && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
          <Clock className="h-3 w-3" />
          {formatDate(match.ended_at)} 終了
        </p>
      )}
    </div>
  );
}

function TeamDisplay({
  team,
  score,
  isWinner,
  isLoser,
  align,
}: {
  team: MatchSummary["team1"];
  score: number;
  isWinner: boolean;
  isLoser: boolean;
  align: "left" | "right";
}) {
  return (
    <div
      className={cn(
        "flex flex-1 items-center gap-3",
        align === "right" && "flex-row-reverse text-right",
        isLoser && "opacity-40",
      )}
    >
      {/* ロゴ */}
      <div className="h-9 w-9 flex-shrink-0 overflow-hidden rounded-lg border border-white/10 bg-white/5 flex items-center justify-center">
        {team?.logo_url ? (
          <img src={team.logo_url} alt={team.name} className="h-full w-full object-contain" />
        ) : (
          <span className="text-xs font-bold text-slate-500">
            {team?.tag?.slice(0, 3) ?? "TBD"}
          </span>
        )}
      </div>

      <div className="min-w-0">
        <p className={cn("truncate text-sm font-bold", isWinner ? "text-brand-400" : "text-white")}>
          {team?.name ?? "TBD"}
        </p>
        {team?.tag && <p className="text-xs text-slate-500">{team.tag}</p>}
      </div>

      {isWinner && (
        <span className="text-lg font-black text-brand-400">{score}</span>
      )}
    </div>
  );
}
