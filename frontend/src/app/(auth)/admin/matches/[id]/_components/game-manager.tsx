"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { MatchDetail, BOFormat } from "@/types/match";
import { ScoreForm } from "./score-form";
import type { useMatchAdmin } from "@/features/matches/hooks/use-match-admin";

const GAME_COUNT: Record<BOFormat, number> = {
  BO1: 1,
  BO3: 3,
  BO5: 5,
};

interface GameManagerProps {
  match: MatchDetail;
  game: string;
  updateScore: ReturnType<typeof useMatchAdmin>["updateScore"];
}

export function GameManager({ match, game, updateScore }: GameManagerProps) {
  const maxGames = GAME_COUNT[match.format];
  const [activeGame, setActiveGame] = useState(1);

  const isDisabled = match.status !== "ongoing";

  const currentGame = match.games.find((g) => g.game_number === activeGame);

  // ゲームの勝者を判定（最高スコアを持つチーム）
  const getGameResult = (gameNum: number) => {
    const g = match.games.find((g) => g.game_number === gameNum);
    if (!g || !g.winner_id) return null;
    return g.winner_id === match.team1?.id ? "team1" : "team2";
  };

  const handleScoreSubmit = async (data: {
    gameNumber: number;
    team1_score: number;
    team2_score: number;
    duration_seconds?: number;
  }) => {
    await updateScore.mutateAsync(data);
  };

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900">
      {/* ゲームタブ */}
      <div className="flex border-b border-white/10">
        {Array.from({ length: maxGames }, (_, i) => i + 1).map((gameNum) => {
          const result = getGameResult(gameNum);
          const isActive = activeGame === gameNum;
          const hasGame = match.games.some((g) => g.game_number === gameNum);

          return (
            <button
              key={gameNum}
              onClick={() => setActiveGame(gameNum)}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "border-brand-500 text-brand-400"
                  : "border-transparent text-slate-500 hover:text-slate-300",
              )}
            >
              Game {gameNum}
              {result && (
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    result === "team1" ? "bg-brand-400" : "bg-red-400",
                  )}
                />
              )}
              {hasGame && !result && (
                <span className="h-2 w-2 rounded-full bg-yellow-400/60" />
              )}
            </button>
          );
        })}
      </div>

      {/* 現在のゲームスコア表示 */}
      {currentGame && (currentGame.team1_score > 0 || currentGame.team2_score > 0) && (
        <div className="border-b border-white/10 bg-white/3 px-5 py-3 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            現在のスコア
            {currentGame.map_name && (
              <span className="ml-2 font-semibold text-slate-400">{currentGame.map_name}</span>
            )}
          </p>
          <p className="text-lg font-black tabular-nums text-white">
            {currentGame.team1_score}
            <span className="mx-1.5 text-slate-600">–</span>
            {currentGame.team2_score}
          </p>
        </div>
      )}

      {/* スコア入力フォーム */}
      <div className="p-5">
        {isDisabled && (
          <div className="mb-4 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-2.5 text-xs text-yellow-400">
            試合がLIVEの場合のみスコアを更新できます
          </div>
        )}

        <ScoreForm
          gameNumber={activeGame}
          team1={match.team1}
          team2={match.team2}
          currentGame={currentGame}
          game={game}
          isDisabled={isDisabled}
          onSubmit={handleScoreSubmit}
        />

        {updateScore.isError && (
          <p className="mt-2 text-xs text-red-400">スコアの更新に失敗しました。再試行してください。</p>
        )}
        {updateScore.isSuccess && (
          <p className="mt-2 text-xs text-green-400">スコアを更新しました</p>
        )}
      </div>
    </div>
  );
}
