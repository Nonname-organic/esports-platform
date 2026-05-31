"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, RefreshCw, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useAdminDashboard } from "@/features/admin/hooks/use-admin";
import { OverviewCards } from "./_components/overview-cards";
import { OperationsPanel } from "./_components/operations-panel";
import { TrendSection } from "./_components/trend-section";
import { ActivityFeed } from "./_components/activity-feed";
import { NotificationPanel } from "./_components/notification-panel";

function PageSkeleton() {
  return (
    <div className="animate-pulse space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-white/5" />
        ))}
      </div>
      <div className="h-40 rounded-xl bg-white/5" />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2 h-96 rounded-xl bg-white/5" />
        <div className="h-96 rounded-xl bg-white/5" />
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const hasRole = useAuthStore((s) => s.hasRole);
  const hasHydrated = useAuthStore((s) => s._hasHydrated);

  // 管理者のみアクセス可能（localStorage読み込み完了後に判定）
  useEffect(() => {
    if (hasHydrated && !hasRole("admin")) {
      router.replace("/dashboard");
    }
  }, [hasHydrated, hasRole, router]);

  const { data, isLoading, isError, refetch, isFetching } = useAdminDashboard();

  // localStorage読み込み前 or admin以外はスケルトン表示
  if (!hasHydrated || !hasRole("admin")) return <PageSkeleton />;

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-6 sm:px-6 lg:px-8">
      {/* ページヘッダー */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-red-500/10 p-2">
            <Shield className="h-6 w-6 text-red-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black text-white">Admin Dashboard</h1>
              <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-400 uppercase">
                Admin Only
              </span>
            </div>
            <p className="text-xs text-slate-500">プラットフォーム全体の運営管理</p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          更新
        </button>
      </div>

      {/* コンテンツ */}
      {isLoading && <PageSkeleton />}

      {isError && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-900 py-24">
          <AlertCircle className="mb-3 h-12 w-12 text-slate-700" />
          <p className="text-sm text-slate-400">ダッシュボードの読み込みに失敗しました</p>
          <button
            onClick={() => refetch()}
            className="mt-4 rounded-lg bg-brand-500/10 px-4 py-2 text-sm text-brand-400 hover:bg-brand-500/20 transition-colors"
          >
            再試行
          </button>
        </div>
      )}

      {!isLoading && !isError && data && (
        <div className="space-y-5">
          {/* KPIカード */}
          <OverviewCards overview={data.overview} />

          {/* 運営指標 */}
          <OperationsPanel ops={data.operations} />

          {/* 月次推移 + 成長率 */}
          <TrendSection
            trends={data.monthly_trends}
            growthMetrics={data.growth_metrics}
          />

          {/* アクティビティ + 通知 (2カラム) */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <ActivityFeed activities={data.recent_activities} />
            <NotificationPanel />
          </div>

          {/* フッター */}
          <div className="border-t border-white/5 pt-4 text-center text-xs text-slate-700">
            Admin Dashboard · データは5分ごとに自動更新
          </div>
        </div>
      )}
    </div>
  );
}
