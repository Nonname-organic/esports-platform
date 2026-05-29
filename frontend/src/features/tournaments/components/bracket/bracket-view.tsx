"use client";

import { cn } from "@/lib/utils";
import type { BracketMatch, BracketResponse } from "@/types/tournament";

interface BracketViewProps {
  bracket: BracketResponse;
  className?: string;
}

export function BracketView({ bracket, className }: BracketViewProps) {
  const rounds = Object.entries(bracket.rounds)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([round, matches]) => ({
      round: Number(round),
      matches: [...matches].sort((a, b) => a.match_number - b.match_number),
    }));

  const totalRounds = rounds.length;

  return (
    <div
      className={cn(
        "flex gap-0 overflow-x-auto pb-4",
        className,
      )}
    >
      {rounds.map(({ round, matches }, roundIndex) => {
        // ラウンドが進むほどマッチ数が半減 → 縦スペースを倍に
        const spacingClass = [
          "gap-4",
          "gap-8",
          "gap-16",
          "gap-32",
          "gap-64",
        ][Math.min(roundIndex, 4)];

        return (
          <div key={round} className="flex flex-col items-center">
            {/* ラウンドヘッダー */}
            <div className="mb-4 w-52 text-center">
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-slate-400">
                {getRoundLabel(round, totalRounds, bracket.format)}
              </span>
            </div>

            {/* マッチリスト */}
            <div className={cn("flex flex-col items-center", spacingClass)}>
              {matches.map((match) => (
                <BracketMatchCard
                  key={match.id}
                  match={match}
                  isLastRound={roundIndex === totalRounds - 1}
                  showConnector={roundIndex < totalRounds - 1}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface BracketMatchCardProps {
  match: BracketMatch;
  isLastRound: boolean;
  showConnector: boolean;
}

function BracketMatchCard({ match, isLastRound, showConnector }: BracketMatchCardProps) {
  const isOngoing = match.status === "ongoing";
  const isCompleted = match.status === "completed";

  return (
    <div className="relative flex items-center">
      <div
        className={cn(
          "w-52 rounded-lg border bg-slate-900 overflow-hidden transition-all",
          isOngoing && "border-red-500/50 shadow-lg shadow-red-500/20",
          isCompleted && "border-white/10",
          !isOngoing && !isCompleted && "border-white/5",
        )}
      >
        {/* 試合番号 */}
        <div className="border-b border-white/5 px-2 py-1">
          <span className="text-xs text-slate-500">
            {isOngoing && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />}
            Round {match.round_number} - Match {match.match_number}
          </span>
        </div>

        {/* Team 1 */}
        <TeamRow
          team={match.team1}
          isWinner={match.winner_id === match.team1?.id}
          isLoser={!!match.winner_id && match.winner_id !== match.team1?.id}
        />

        {/* 区切り */}
        <div className="border-t border-white/5" />

        {/* Team 2 */}
        <TeamRow
          team={match.team2}
          isWinner={match.winner_id === match.team2?.id}
          isLoser={!!match.winner_id && match.winner_id !== match.team2?.id}
        />
      </div>

      {/* 接続線（右側へのコネクター） */}
      {showConnector && (
        <div className="absolute right-0 top-1/2 h-px w-4 -translate-y-1/2 bg-white/20" />
      )}
    </div>
  );
}

interface TeamRowProps {
  team: BracketMatch["team1"];
  isWinner: boolean;
  isLoser: boolean;
}

function TeamRow({ team, isWinner, isLoser }: TeamRowProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 transition-colors",
        isWinner && "bg-green-500/10",
        isLoser && "opacity-40",
        !team && "opacity-30",
      )}
    >
      {/* チームロゴ */}
      {team?.logo_url ? (
        <img src={team.logo_url} alt={team.name ?? ""} className="h-6 w-6 rounded-sm object-contain" />
      ) : (
        <div className="h-6 w-6 rounded-sm bg-white/10 flex items-center justify-center">
          <span className="text-[10px] font-bold text-slate-500">
            {team?.tag?.slice(0, 2) ?? "TBD"}
          </span>
        </div>
      )}

      {/* チーム名 */}
      <div className="flex-1 min-w-0">
        {team ? (
          <>
            <p className={cn("truncate text-sm font-semibold", isWinner && "text-green-400")}>
              {team.name}
            </p>
            <p className="text-xs text-slate-500">{team.tag}</p>
          </>
        ) : (
          <p className="text-sm text-slate-600">TBD</p>
        )}
      </div>

      {/* 勝者マーク */}
      {isWinner && <span className="text-green-400 text-sm">✓</span>}
    </div>
  );
}

function getRoundLabel(round: number, total: number, format: string): string {
  if (format === "round_robin") return `第${round}試合`;
  const fromEnd = total - round;
  if (fromEnd === 0) return "決勝";
  if (fromEnd === 1) return "準決勝";
  if (fromEnd === 2) return "準々決勝";
  return `Round ${round}`;
}
