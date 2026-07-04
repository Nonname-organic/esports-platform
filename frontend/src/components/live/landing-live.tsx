"use client";

import type { TournamentSummary } from "@/types/tournament";
import { LiveProvider } from "@/features/live/provider/live-provider";
import { LiveStatusBar } from "./live-status-bar";
import { StatisticsCard } from "./statistics-card";
import { LiveTournamentPreview } from "./live-tournament-preview";
import { LiveActivityFeed } from "./live-activity-feed";

/**
 * ランディングのライブ体験島（client）。
 * LiveProvider（60秒Polling / Visibility対応 / WS差し替え可）配下に
 * Live Status Bar → Statistics Card → Live Tournament Preview を配置し、
 * Live Activity は画面右下に固定表示する。
 */
export function LandingLive({ initialFeatured }: { initialFeatured: TournamentSummary[] }) {
  return (
    <LiveProvider intervalMs={60000}>
      <LiveStatusBar />
      <StatisticsCard />
      <LiveTournamentPreview initial={initialFeatured} />
      <LiveActivityFeed />
    </LiveProvider>
  );
}
