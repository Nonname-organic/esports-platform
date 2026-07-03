"use client";

import { useState } from "react";
import { Map as MapIcon } from "lucide-react";
import { useCompetitive } from "@/features/riot/hooks/use-riot";
import { usePlayerCareer } from "@/features/career/hooks/use-career";
import { SourceToggle, type StatSource } from "./shared/source-toggle";
import { MapCard, type MapCardData } from "./shared/map-card";
import { EmptyState } from "./shared/empty-state";

export function PlayerMaps({ playerId }: { playerId: string }) {
  const [source, setSource] = useState<StatSource>("competitive");
  const { data: comp, isLoading: compLoading } = useCompetitive(playerId);
  const { data: career, isLoading: careerLoading } = usePlayerCareer(playerId);

  const isLoading = source === "competitive" ? compLoading : careerLoading;

  const maps: MapCardData[] = source === "competitive"
    ? (comp?.maps ?? []).map((m) => ({
        map: m.map, games: m.games, win_rate: m.win_rate, acs: m.acs, kd: m.kd, kda: m.kda,
        attack_win_rate: m.attack_win_rate, defense_win_rate: m.defense_win_rate, first_kill_rate: m.first_kill_rate,
      }))
    : (career?.map_performance ?? []).map((m) => ({
        map: m.map_name, games: m.games, win_rate: m.win_rate, acs: null, kd: null, kda: null,
        attack_win_rate: null, defense_win_rate: null, first_kill_rate: null,
      }));

  return (
    <div className="space-y-5 pt-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-brand-500/10 p-1.5"><MapIcon className="h-4 w-4 text-brand-400" /></div>
          <h2 className="text-sm font-bold text-white">Maps</h2>
        </div>
        <SourceToggle value={source} onChange={setSource} />
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-40 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : maps.length === 0 ? (
        <EmptyState icon={MapIcon} title="マップデータがありません"
          desc={source === "competitive" ? "Riot連携・同期後に表示されます。" : "大会参加後に表示されます。"} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {maps.map((m) => <MapCard key={m.map} data={m} />)}
        </div>
      )}
    </div>
  );
}
