"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";

interface RoundHistoryTabProps {
  match: MatchDetail;
}

// ラウンドデータ型
interface RoundData {
  round_number: number;
  winner_side: "attack" | "defense" | null;
  win_condition: "elimination" | "bomb" | "time" | null;
  team1_economy?: { type: "eco" | "half_buy" | "full_buy"; total: number };
  team2_economy?: { type: "eco" | "half_buy" | "full_buy"; total: number };
  clutch?: { player: string; vs: number };
}

const WIN_CONDITION_ICON: Record<string, string> = {
  elimination: "💀",
  bomb: "💣",
  time: "⏱️",
};

const ECONOMY_COLORS: Record<string, string> = {
  eco: "bg-red-500/80",
  half_buy: "bg-yellow-500/80",
  full_buy: "bg-green-500/80",
};

export function RoundHistoryTab({ match }: RoundHistoryTabProps) {
  const [selectedGame, setSelectedGame] = useState(0);

  const game = match.games[selectedGame];
  const totalRounds = (game?.team1_score ?? 0) + (game?.team2_score ?? 0);

  // ラウンドデータをシミュレート（実際はAPIから取得）
  const rounds: RoundData[] = Array.from({ length: totalRounds }, (_, i) => ({
    round_number: i + 1,
    winner_side: i % 3 === 0 ? "attack" : "defense",
    win_condition: i % 5 === 0 ? "bomb" : i % 7 === 0 ? "time" : "elimination",
    team1_economy: { type: i < 5 ? "eco" : i < 10 ? "half_buy" : "full_buy", total: i * 4700 },
    team2_economy: { type: i < 3 ? "eco" : i < 8 ? "half_buy" : "full_buy", total: i * 5000 },
  }));

  // ハーフタイムで分割
  const HALF = Math.ceil(totalRounds / 2);
  const firstHalf = rounds.slice(0, HALF);
  const secondHalf = rounds.slice(HALF);

  const team1Wins = match.games[selectedGame]?.winner_id === match.team1?.id
    ? match.games[selectedGame]?.team1_score
    : match.games[selectedGame]?.team2_score;

  return (
    <div className="pt-4 space-y-5">
      {/* ゲームタブ */}
      {match.games.length > 1 && (
        <div className="flex gap-2">
          {match.games.map((g, i) => (
            <button
              key={g.id}
              onClick={() => setSelectedGame(i)}
              className={cn(
                "rounded-lg border px-4 py-2 text-sm font-semibold transition-colors",
                selectedGame === i ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-white/10 text-slate-400 hover:text-white",
              )}
            >
              {g.map_name ?? `Map ${i + 1}`}
            </button>
          ))}
        </div>
      )}

      {totalRounds === 0 ? (
        <div className="flex h-40 items-center justify-center rounded-xl border border-white/10 bg-slate-900">
          <p className="text-sm text-slate-500">ラウンドデータがありません</p>
        </div>
      ) : (
        <>
          {/* ラウンドタイムライン */}
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-white">ラウンドタイムライン</h3>

            {[{ label: "1st Half", rounds: firstHalf }, { label: "2nd Half", rounds: secondHalf }].map(({ label, rounds: halfRounds }) => (
              <div key={label} className="mb-4">
                <p className="mb-2 text-xs text-slate-500">{label}</p>
                <div className="flex flex-wrap gap-1">
                  {halfRounds.map((round) => (
                    <div
                      key={round.round_number}
                      title={`Round ${round.round_number}: ${round.win_condition} (${round.winner_side})`}
                      className={cn(
                        "flex h-8 w-8 flex-shrink-0 cursor-pointer items-center justify-center rounded-lg text-xs font-bold transition-all hover:scale-110",
                        round.winner_side === "attack" ? "bg-red-500/20 text-red-400 border border-red-500/30" : "bg-blue-500/20 text-blue-400 border border-blue-500/30",
                      )}
                    >
                      {WIN_CONDITION_ICON[round.win_condition ?? "elimination"]}
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* 凡例 */}
            <div className="flex flex-wrap gap-4 border-t border-white/10 pt-3 text-xs text-slate-500">
              <span className="flex items-center gap-1"><span className="h-3 w-3 rounded bg-red-500/30" />ATK Win</span>
              <span className="flex items-center gap-1"><span className="h-3 w-3 rounded bg-blue-500/30" />DEF Win</span>
              <span>💀 Elimination &nbsp; 💣 Bomb &nbsp; ⏱️ Time</span>
            </div>
          </div>

          {/* エコノミーグラフ */}
          <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-white">エコノミーチャート</h3>
            <div className="space-y-2">
              {/* Team 1 */}
              <div className="flex items-center gap-3">
                <span className="w-16 flex-shrink-0 truncate text-xs text-slate-400">{match.team1?.tag}</span>
                <div className="flex flex-1 gap-0.5 overflow-x-auto">
                  {rounds.map((r) => (
                    <div
                      key={r.round_number}
                      title={`${r.team1_economy?.type} (¥${(r.team1_economy?.total ?? 0).toLocaleString()})`}
                      className={cn("h-6 w-6 flex-shrink-0 rounded-sm", ECONOMY_COLORS[r.team1_economy?.type ?? "eco"])}
                    />
                  ))}
                </div>
              </div>
              {/* Team 2 */}
              <div className="flex items-center gap-3">
                <span className="w-16 flex-shrink-0 truncate text-xs text-slate-400">{match.team2?.tag}</span>
                <div className="flex flex-1 gap-0.5 overflow-x-auto">
                  {rounds.map((r) => (
                    <div
                      key={r.round_number}
                      title={`${r.team2_economy?.type} (¥${(r.team2_economy?.total ?? 0).toLocaleString()})`}
                      className={cn("h-6 w-6 flex-shrink-0 rounded-sm", ECONOMY_COLORS[r.team2_economy?.type ?? "eco"])}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-3 flex gap-4 text-xs text-slate-500">
              <span><span className="inline-block h-2 w-3 rounded bg-red-500/80 mr-1" />Eco</span>
              <span><span className="inline-block h-2 w-3 rounded bg-yellow-500/80 mr-1" />Half Buy</span>
              <span><span className="inline-block h-2 w-3 rounded bg-green-500/80 mr-1" />Full Buy</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
