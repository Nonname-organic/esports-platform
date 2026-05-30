import { Suspense } from "react";
import type { Metadata } from "next";
import { TournamentsClient } from "./_components/tournaments-client";
import { TournamentGridSkeleton } from "@/features/tournaments/components/tournament-skeleton";

export const metadata: Metadata = {
  title: "大会一覧 | EsportsPlatform",
  description: "参加・観戦できる e-スポーツ大会を探す",
};

export default function TournamentsPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <TournamentsClient />
    </Suspense>
  );
}

function PageSkeleton() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8 space-y-2">
        <div className="h-9 w-40 animate-pulse rounded-lg bg-white/5" />
        <div className="h-5 w-64 animate-pulse rounded-lg bg-white/5" />
      </div>
      <div className="mb-6 space-y-3">
        <div className="h-10 w-full animate-pulse rounded-lg bg-white/5" />
        <div className="h-10 w-full animate-pulse rounded-xl bg-white/5" />
      </div>
      <TournamentGridSkeleton count={12} />
    </div>
  );
}
