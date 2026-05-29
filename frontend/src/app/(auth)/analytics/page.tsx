"use client";

// 統計分析ダッシュボード: CSR
// TanStack Query でフィルタリング。Recharts でデータ可視化。

import { useState } from "react";
import { BarChart3 } from "lucide-react";
import { MapWinRateChart, CompositionTable, RankingTable, PlayerRadarChart } from "@/features/analytics/components/analytics-dashboard";
import { useMapStats, useCompositions, useRankings } from "@/features/analytics/hooks/use-analytics";
import { useTournaments } from "@/features/tournaments/hooks/use-tournaments";
import type { GameType } from "@/types/tournament";
import { cn } from "@/lib/utils";

const GAMES: GameType[] = ["VALORANT", "LOL", "APEX", "CS2", "OVERWATCH"];

export default function AnalyticsPage() {
  const [selectedGame, setSelectedGame] = useState<GameType>("VALORANT");
  const [selectedTournamentId, setSelectedTournamentId] = useState<string>("");

  const { data: mapStatsData, isLoading: isLoadingMaps } = useMapStats(selectedGame);
  const { data: compositionsData, isLoading: isLoadingComps } = useCompositions(selectedGame);
  const { data: rankingsData, isLoading: isLoadingRankings } = useRankings(selectedTournamentId);
  const { data: tournamentsData } = useTournaments();

  const tournaments = tournamentsData?.pages.flatMap((p) => p.data) ?? [];
  const mapStats = mapStatsData ?? [];
  const compositions = compositionsData ?? [];
  const rankings = rankingsData ?? [];

  return (
    <div className="px-4 py-8 sm:px-6 lg:px-8">
      {/* ページヘッダー */}
      <div className="mb-8">
        <h1 className="text-2xl font-black text-white">統計分析</h1>
        <p className="mt-0.5 text-sm text-slate-400">
          マップ勝率・エージェント構成・ランキングをゲーム別に分析
        </p>
      </div>

      {/* ゲームセレクター */}
      <div className="mb-6 flex items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1 w-fit">
        {GAMES.map((game) => (
          <button
            key={game}
            onClick={() => setSelectedGame(game)}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
              selectedGame === game
                ? "bg-brand-500 text-white"
                : "text-slate-400 hover:text-white",
            )}
          >
            {game}
          </button>
        ))}
      </div>

      {/* マップ勝率チャート */}
      <div className="mb-6">
        {isLoadingMaps ? (
          <div className="h-80 animate-pulse rounded-xl bg-white/5" />
        ) : mapStats.length > 0 ? (
          <MapWinRateChart data={mapStats} />
        ) : (
          <EmptyState message="マップデータがありません" />
        )}
      </div>

      {/* 構成勝率 + ランキング */}
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* エージェント構成 */}
        {isLoadingComps ? (
          <div className="h-80 animate-pulse rounded-xl bg-white/5" />
        ) : (
          <CompositionTable data={compositions} />
        )}

        {/* 大会別ランキング */}
        <div className="flex flex-col gap-4">
          {/* 大会セレクター */}
          <div className="rounded-xl border border-white/10 bg-slate-900 p-4">
            <label className="mb-2 block text-sm font-semibold text-white">ランキング表示 (大会)</label>
            <select
              value={selectedTournamentId}
              onChange={(e) => setSelectedTournamentId(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
            >
              <option value="">大会を選択してください</option>
              {tournaments
                .filter((t) => t.game === selectedGame)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
            </select>
          </div>

          {selectedTournamentId ? (
            isLoadingRankings ? (
              <div className="h-48 animate-pulse rounded-xl bg-white/5" />
            ) : (
              <RankingTable data={rankings} title="チームランキング" />
            )
          ) : (
            <div className="rounded-xl border border-white/10 bg-slate-900 py-8 text-center">
              <BarChart3 className="mx-auto mb-2 h-8 w-8 text-slate-600" />
              <p className="text-sm text-slate-500">大会を選択するとランキングが表示されます</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-48 items-center justify-center rounded-xl border border-white/10 bg-slate-900">
      <div className="text-center">
        <BarChart3 className="mx-auto mb-2 h-8 w-8 text-slate-600" />
        <p className="text-sm text-slate-500">{message}</p>
      </div>
    </div>
  );
}
