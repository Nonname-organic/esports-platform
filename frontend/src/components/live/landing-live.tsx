"use client";

import type { TournamentSummary } from "@/types/tournament";
import { LiveProvider } from "@/features/live/provider/live-provider";
import { HeroSection } from "@/components/hero/hero-section";
import { LiveTournamentPreview } from "./live-tournament-preview";

/**
 * ランディング（client）— シンプル導線。
 * Hero（背景動画 + 受付カウンター ENTRY OPEN 1枚 + CTA）で第一印象を作り、
 * その直下に「開催中の大会」だけを置く最小構成。
 * ※ LiveProvider は Hero 内のライブ指標（開催中/進行中/オンライン）で使用。
 */
export function LandingLive({ initialFeatured }: { initialFeatured: TournamentSummary[] }) {
  return (
    <LiveProvider intervalMs={60000}>
      <HeroSection />

      {/* スクロール到達点（Hero の Explore Live Tournament から遷移） */}
      <div id="live" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-12">
        <LiveTournamentPreview initial={initialFeatured} />
      </div>
    </LiveProvider>
  );
}
