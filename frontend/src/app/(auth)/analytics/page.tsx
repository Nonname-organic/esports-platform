"use client";

import { Suspense } from "react";
import { BarChart3, RefreshCw } from "lucide-react";
import { FilterBar } from "./_components/filter-bar";
import { KpiCards } from "./_components/kpi-cards";
import { TrendSection } from "./_components/trend-section";
import { MapSection } from "./_components/map-section";
import { AgentSection } from "./_components/agent-section";
import { HeatMapSection } from "./_components/heatmap-section";
import { RankingsSection } from "./_components/rankings-section";

// ── スケルトン ────────────────────────────────────────────────────────────────
function SectionSkeleton({ h = 72 }: { h?: number }) {
  return (
    <div
      className="animate-pulse rounded-xl bg-white/5"
      style={{ height: `${h * 4}px` }}
    />
  );
}

// ── メインページ ──────────────────────────────────────────────────────────────
export default function AnalyticsDashboardPage() {
  return (
    <div className="min-h-screen bg-slate-950 px-4 py-6 sm:px-6 lg:px-8">
      {/* ページヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-brand-500/10 p-2">
            <BarChart3 className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">Analytics Dashboard</h1>
            <p className="text-xs text-slate-500">
              BIツール · リアルタイム統計分析
            </p>
          </div>
        </div>

        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          更新
        </button>
      </div>

      <div className="space-y-5">
        {/* ── フィルターバー ── */}
        <Suspense fallback={<div className="h-12 animate-pulse rounded-xl bg-white/5" />}>
          <FilterBar />
        </Suspense>

        {/* ── KPI カード ── */}
        <Suspense fallback={
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        }>
          <KpiCards />
        </Suspense>

        {/* ── トレンド ── */}
        <Suspense fallback={<SectionSkeleton h={72} />}>
          <TrendSection />
        </Suspense>

        {/* ── MAP / Agent 2カラム ── */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Suspense fallback={<SectionSkeleton h={80} />}>
            <MapSection />
          </Suspense>
          <Suspense fallback={<SectionSkeleton h={80} />}>
            <AgentSection />
          </Suspense>
        </div>

        {/* ── ヒートマップ ── */}
        <Suspense fallback={<SectionSkeleton h={48} />}>
          <HeatMapSection />
        </Suspense>

        {/* ── ランキング ── */}
        <Suspense fallback={
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <SectionSkeleton h={64} />
            <SectionSkeleton h={64} />
          </div>
        }>
          <RankingsSection />
        </Suspense>
      </div>

      {/* フッター */}
      <div className="mt-8 border-t border-white/5 pt-4 text-center text-xs text-slate-700">
        EsportsPlatform Analytics · データは10分ごとにキャッシュ更新
      </div>
    </div>
  );
}
