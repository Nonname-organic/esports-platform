"use client";

import type { TournamentSummary } from "@/types/tournament";
import { LiveProvider } from "@/features/live/provider/live-provider";
import { HeroSection } from "@/components/hero/hero-section";
import { LiveActivityTicker } from "./live-activity-ticker";
import { SocialProofBar } from "./social-proof-bar";
import { EntryOpenTournaments } from "./entry-open-tournaments";
import { WinnerHighlight } from "./winner-highlight";
import { LiveStatusBar } from "./live-status-bar";
import { StatisticsCard } from "./statistics-card";
import { LiveTournamentPreview } from "./live-tournament-preview";
import { LiveActivityFeed } from "./live-activity-feed";

/**
 * ランディングのライブ体験島（client）。
 * 単一の LiveProvider（60秒Polling / Visibility対応 / WS・SSE差し替え可能な Transport）配下に
 * Hero（背景動画＋受付バナー）と各ライブセクションを配置する。
 * ※ Provider / Transport の公開IFは不変（Consumer変更なし）。
 *
 * 感情設計の並び: 受付会場として「今参加できる大会 → 証明 → 王者 → 進行状況」の順に配置。
 */
export function LandingLive({ initialFeatured }: { initialFeatured: TournamentSummary[] }) {
  return (
    <LiveProvider intervalMs={60000}>
      <HeroSection />

      {/* スクロール到達点（Hero の Explore Live Tournament から遷移） */}
      <div id="live" className="mx-auto max-w-7xl scroll-mt-20 space-y-10 px-4 py-12">
        <LiveActivityTicker />
        <SocialProofBar />
        <EntryOpenTournaments />
        <WinnerHighlight />
        <LiveStatusBar />
        <StatisticsCard />
        <LiveTournamentPreview initial={initialFeatured} />
      </div>

      <LiveActivityFeed />
    </LiveProvider>
  );
}
