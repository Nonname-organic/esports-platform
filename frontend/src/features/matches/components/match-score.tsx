"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { MatchDetail, MatchGame } from "@/types/match";

interface MatchScoreProps {
  match: MatchDetail;
  isLive?: boolean;
}

export function MatchScore({ match, isLive }: MatchScoreProps) {
  const [selectedGame, setSelectedGame] = useState<number>(0);

  const team1GameWins = match.games.filter((g) => g.winner_id === match.team1?.id).length;
  const team2GameWins = match.games.filter((g) => g.winner_id === match.team2?.id).length;

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900 overflow-hidden">
      {/* メインスコアボード */}
      <div className="relative bg-gradient-to-b from-slate-800 to-slate-900 p-6">
        {isLive && (
          <div className="absolute left-1/2 top-3 -translate-x-1/2 flex items-center gap-1.5 rounded-full bg-red-500 px-3 py-0.5 text-xs font-bold text-white">
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
            LIVE
          </div>
        )}

        <div className="flex items-center justify-between gap-4 pt-4">
          {/* Team 1 */}
          <TeamScore
            team={match.team1}
            gameWins={team1GameWins}
            isWinner={match.winner_id === match.team1?.id}
            align="left"
          />

          {/* スコアセンター */}
          <div className="flex flex-col items-center gap-1">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "text-5xl font-black tabular-nums",
                  match.winner_id === match.team1?.id ? "text-green-400" : "text-white",
                )}
              >
                {team1GameWins}
              </span>
              <span className="text-2xl font-thin text-slate-600">:</span>
              <span
                className={cn(
                  "text-5xl font-black tabular-nums",
                  match.winner_id === match.team2?.id ? "text-green-400" : "text-white",
                )}
              >
                {team2GameWins}
              </span>
            </div>
            <span className="text-xs text-slate-500">{match.format}</span>
          </div>

          {/* Team 2 */}
          <TeamScore
            team={match.team2}
            gameWins={team2GameWins}
            isWinner={match.winner_id === match.team2?.id}
            align="right"
          />
        </div>
      </div>

      {/* ゲームタブ */}
      {match.games.length > 0 && (
        <>
          <div className="flex border-t border-white/10">
            {match.games.map((game, i) => (
              <button
                key={game.id}
                onClick={() => setSelectedGame(i)}
                className={cn(
                  "flex-1 py-3 text-sm font-medium transition-colors",
                  selectedGame === i
                    ? "border-b-2 border-brand-500 text-white"
                    : "text-slate-500 hover:text-slate-300",
                )}
              >
                <span className="block">Game {game.game_number}</span>
                {game.map_name && (
                  <span className="block text-xs opacity-60">{game.map_name}</span>
                )}
              </button>
            ))}
          </div>

          {/* 選択中ゲームの詳細 */}
          {match.games[selectedGame] && (
            <GameDetail
              game={match.games[selectedGame]}
              team1={match.team1}
              team2={match.team2}
            />
          )}
        </>
      )}
    </div>
  );
}

interface TeamScoreProps {
  team: MatchDetail["team1"];
  gameWins: number;
  isWinner: boolean;
  align: "left" | "right";
}

function TeamScore({ team, gameWins, isWinner, align }: TeamScoreProps) {
  return (
    <div className={cn("flex flex-col items-center gap-2", align === "right" && "")}>
      {team?.logo_url ? (
        <img src={team.logo_url} alt={team.name} className="h-16 w-16 object-contain" />
      ) : (
        <div className="h-16 w-16 rounded-xl bg-white/10 flex items-center justify-center">
          <span className="text-lg font-bold text-slate-400">{team?.tag ?? "TBD"}</span>
        </div>
      )}
      <div className={cn("text-center", align === "right" && "")}>
        <p className={cn("font-bold text-sm", isWinner ? "text-green-400" : "text-white")}>
          {team?.name ?? "TBD"}
        </p>
        <p className="text-xs text-slate-500">{team?.tag ?? ""}</p>
      </div>
      {isWinner && (
        <span className="rounded-full bg-green-500/20 px-2 py-0.5 text-xs font-semibold text-green-400">
          WIN
        </span>
      )}
    </div>
  );
}

interface GameDetailProps {
  game: MatchGame;
  team1: MatchDetail["team1"];
  team2: MatchDetail["team2"];
}

function GameDetail({ game, team1, team2 }: GameDetailProps) {
  const team1Players = game.player_stats.filter((p) => p.team_id === team1?.id);
  const team2Players = game.player_stats.filter((p) => p.team_id === team2?.id);

  return (
    <div className="p-4">
      {/* ゲームスコア */}
      <div className="mb-4 flex items-center justify-between rounded-lg bg-white/5 px-4 py-2">
        <span className="text-lg font-bold text-white">{game.team1_score}</span>
        <span className="text-xs text-slate-500">
          {game.map_name ?? "Map"} •{" "}
          {game.duration_seconds
            ? `${Math.floor(game.duration_seconds / 60)}分`
            : "進行中"}
        </span>
        <span className="text-lg font-bold text-white">{game.team2_score}</span>
      </div>

      {/* 選手スタッツ */}
      {game.player_stats.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          <PlayerStatsTable players={team1Players} teamName={team1?.name ?? ""} />
          <PlayerStatsTable players={team2Players} teamName={team2?.name ?? ""} />
        </div>
      )}
    </div>
  );
}

function PlayerStatsTable({
  players,
  teamName,
}: {
  players: MatchGame["player_stats"];
  teamName: string;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
        {teamName}
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-500">
            <th className="text-left pb-1">選手</th>
            <th className="text-center pb-1">K</th>
            <th className="text-center pb-1">D</th>
            <th className="text-center pb-1">A</th>
            <th className="text-right pb-1">KDA</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {players
            .sort((a, b) => b.score - a.score)
            .map((p) => (
              <tr key={p.player_id} className="hover:bg-white/5">
                <td className="py-1">
                  <div className="flex items-center gap-1.5">
                    {p.agent && (
                      <span className="rounded bg-white/10 px-1 text-[10px] text-slate-400">
                        {p.agent.slice(0, 4)}
                      </span>
                    )}
                    <span className="truncate font-medium text-white text-xs">
                      {p.player_name}
                    </span>
                  </div>
                </td>
                <td className="text-center text-green-400 font-mono text-xs">{p.kills}</td>
                <td className="text-center text-red-400 font-mono text-xs">{p.deaths}</td>
                <td className="text-center text-blue-400 font-mono text-xs">{p.assists}</td>
                <td className="text-right font-bold text-white text-xs">
                  {p.kda.toFixed(2)}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
