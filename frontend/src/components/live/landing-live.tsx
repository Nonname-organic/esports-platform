"use client";

import type { TournamentSummary } from "@/types/tournament";
import { LiveProvider } from "@/features/live/provider/live-provider";
import { HeroSection } from "@/components/hero/hero-section";
import { FomoStrip } from "./fomo-strip";
import { FeaturedTournamentBanner } from "./featured-tournament-banner";
import { LiveActivityTicker } from "./live-activity-ticker";
import { SocialProofBar } from "./social-proof-bar";
import { EntryOpenTournaments } from "./entry-open-tournaments";
import { LiveBracketSnapshot } from "./live-bracket-snapshot";
import { WinnerHighlight } from "./winner-highlight";
import { LiveStatusBar } from "./live-status-bar";
import { StatisticsCard } from "./statistics-card";
import { LiveTournamentPreview } from "./live-tournament-preview";
import { LiveActivityFeed } from "./live-activity-feed";
import { HomePersonalized } from "@/components/home/home-personalized";

/**
 * ランディングのライブ体験島（client）。
 * 単一 LiveProvider（60秒Polling / Visibility対応 / WS・SSE差し替え可能な Transport）配下に配置。
 * ※ Provider / Transport の公開IFは不変（Consumer変更なし）。
 *
 * 感情設計の並び: FOMO → 目玉大会 → ライブ活動 → 社会的証明 → 受付 → 進行 → 王者 → 詳細。
 */
export function LandingLive({ initialFeatured }: { initialFeatured: TournamentSummary[] }) {
  return (
    <LiveProvider intervalMs={60000}>
      <HeroSection />

      {/* スクロール到達点（Hero の Explore Live Tournament から遷移） */}
      <div id="live" className="mx-auto max-w-7xl scroll-mt-20 space-y-10 px-4 py-12">
        {/* ホーム・パーソナライズ（ADR-0019 / おすすめ・AI予測・トレンド） */}
        <HomePersonalized />

        <FomoStrip />
        <FeaturedTournamentBanner />
        <LiveActivityTicker />
        <SocialProofBar />
        <EntryOpenTournaments />
        <LiveBracketSnapshot />
        <WinnerHighlight />
        <LiveStatusBar />
        <StatisticsCard />
        <LiveTournamentPreview initial={initialFeatured} />
      </div>

      <LiveActivityFeed />
    </LiveProvider>
  );
}
