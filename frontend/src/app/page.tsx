import { serverFetch } from "@/lib/api-client";
import { LandingLive } from "@/components/live/landing-live";
import type { ListResponse, TournamentSummary } from "@/types/tournament";

import type { Metadata } from "next";

// 公開する3ページのうちの1つ（frontend/src/app/robots.ts の ALLOW と対応）。
// robots と canonical をルートの layout に置くと全ページへ降りてしまうため、
// 公開するページだけがここで宣言する。
export const metadata: Metadata = {
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
};

// ISR: 5分ごとに再生成
export const revalidate = 300;

async function getFeaturedTournaments(): Promise<TournamentSummary[]> {
  try {
    const res = await serverFetch<ListResponse<TournamentSummary>>(
      "/api/v1/tournaments?status=ongoing&limit=3",
      undefined,
      { next: { revalidate: 300 } },
    );
    return res.data;
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const featured = await getFeaturedTournaments();

  return <LandingLive initialFeatured={featured} />;
}
