"use client";

import { useHome } from "@/features/home/hooks/use-home";
import { YourNextTournament } from "./your-next-tournament";
import { RecommendationsRow } from "./recommendations-row";
import { AiPrediction } from "./ai-prediction";
import { TrendingNow } from "./trending-now";
import { AiInsights } from "./ai-insights";

/**
 * ホーム・パーソナライズ島（ADR-0019 / Read Model・Provider集約）。
 * 1リクエスト（/home）で各 Widget の slice を取得し、独立 Widget を合成する。
 */
export function HomePersonalized({ game }: { game?: string }) {
  const { data, isLoading } = useHome(game);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-64 animate-pulse rounded-3xl border border-white/10 bg-white/[0.03]" />
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="h-56 animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />
          <div className="h-56 animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />
        </div>
      </div>
    );
  }
  if (!data) return null;

  const recs = data.recommendations ?? [];
  const next = recs[0];
  const rest = recs.slice(1);

  return (
    <div className="space-y-8">
      {next && <YourNextTournament rec={next} />}

      <div className="grid gap-6 lg:grid-cols-2">
        {data.predictions?.favorite && <AiPrediction pred={data.predictions} />}
        {data.insights?.length > 0 && <AiInsights insights={data.insights} />}
      </div>

      {data.trending && <TrendingNow trending={data.trending} />}

      {rest.length > 0 && <RecommendationsRow title="Upcoming For You" recs={rest} />}
    </div>
  );
}
