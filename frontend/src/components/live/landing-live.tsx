"use client";

import type { TournamentSummary } from "@/types/tournament";
import { LiveProvider } from "@/features/live/provider/live-provider";
import { HeroSection } from "@/components/hero/hero-section";
import { LiveStatusBar } from "./live-status-bar";
import { StatisticsCard } from "./statistics-card";
import { LiveTournamentPreview } from "./live-tournament-preview";
import { LiveActivityFeed } from "./live-activity-feed";

/**
 * ランディングのライブ体験島（client）。
 * 単一の LiveProvider（60秒Polling / Visibility対応 / WS・SSE差し替え可能な Transport）配下に
 * Hero（背景動画＋リアルタイム要素）と各ライブセクションを配置する。
 * ※ Provider / Transport の公開IFは不変（Consumer変更なし）。
 */
export function LandingLive({ initialFeatured }: { initialFeatured: TournamentSummary[] }) {
  return (
    <LiveProvider intervalMs={60000}>
      <HeroSection />

      {/* スクロール到達点（Hero の Explore Live Tournament から遷移） */}
      <div id="live" className="mx-auto max-w-7xl scroll-mt-20 space-y-10 px-4 py-12">
        <LiveStatusBar />
        <StatisticsCard />
        <LiveTournamentPreview initial={initialFeatured} />
      </div>

      <LiveActivityFeed />
    </LiveProvider>
  );
}
