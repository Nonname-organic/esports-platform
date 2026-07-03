"use client";

import { CareerTab } from "./career-tab";
import { AchievementsTab } from "./achievements-tab";

/**
 * Tournament タブ。
 * 既存の大会分析（CareerTab: KPI・戦績・エージェント使用率・マップ勝率）を維持しつつ、
 * 実績（AchievementsTab: 大会成績・順位）を統合表示する。
 */
export function PlayerTournament({ playerId }: { playerId: string }) {
  return (
    <div className="space-y-8">
      <CareerTab playerId={playerId} />
      <div>
        <h2 className="mb-1 mt-2 text-sm font-bold text-white">大会実績</h2>
        <AchievementsTab playerId={playerId} />
      </div>
    </div>
  );
}
