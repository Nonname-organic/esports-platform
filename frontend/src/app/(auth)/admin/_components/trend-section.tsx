"use client";

import { useState } from "react";
import { TrendingUp, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { MonthlyTrendChart } from "@/features/admin/components/monthly-trend-chart";
import { GrowthChart } from "@/features/admin/components/growth-chart";
import type { MonthlyTrend, GrowthMetric } from "@/types/admin";

type View = "trend" | "growth";

interface TrendSectionProps {
  trends: MonthlyTrend[];
  growthMetrics: GrowthMetric[];
}

export function TrendSection({ trends, growthMetrics }: TrendSectionProps) {
  const [view, setView] = useState<View>("trend");

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-brand-500/10 p-1.5">
            <TrendingUp className="h-4 w-4 text-brand-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">
              {view === "trend" ? "月次推移" : "成長率分析"}
            </h2>
            <p className="text-xs text-slate-500">
              {view === "trend" ? "大会・試合・MAU・参加率" : "前月比成長率（%）"}
            </p>
          </div>
        </div>

        {/* ビュー切替 */}
        <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/3 p-0.5">
          <button
            onClick={() => setView("trend")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              view === "trend" ? "bg-brand-500/20 text-brand-400" : "text-slate-500 hover:text-white",
            )}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            推移
          </button>
          <button
            onClick={() => setView("growth")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              view === "growth" ? "bg-brand-500/20 text-brand-400" : "text-slate-500 hover:text-white",
            )}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            成長率
          </button>
        </div>
      </div>

      <div className="px-5 py-4">
        {trends.length === 0 ? (
          <div className="flex h-64 items-center justify-center">
            <p className="text-sm text-slate-500">データがありません</p>
          </div>
        ) : view === "trend" ? (
          <>
            <MonthlyTrendChart data={trends} />
            {/* 凡例補足 */}
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
              {[
                { color: "#3b82f6", label: "大会数" },
                { color: "#22c55e", label: "試合数" },
                { color: "#8b5cf6", label: "新規チーム" },
                { color: "#f59e0b", label: "MAU" },
                { color: "#ef4444", label: "参加率" },
              ].map(({ color, label }) => (
                <span key={label} className="flex items-center gap-1">
                  <span className="inline-block h-2 w-3 rounded" style={{ background: color }} />
                  {label}
                </span>
              ))}
            </div>
          </>
        ) : (
          <>
            <GrowthChart data={growthMetrics} />
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {growthMetrics.map((m) => {
                const isPos = m.growth_rate >= 0;
                return (
                  <div key={m.label} className="rounded-lg bg-white/3 px-3 py-2.5 text-center">
                    <p className="text-xs text-slate-500">{m.label}</p>
                    <p className={cn("mt-0.5 text-lg font-black", isPos ? "text-green-400" : "text-red-400")}>
                      {isPos ? "+" : ""}{m.growth_rate.toFixed(1)}%
                    </p>
                    <p className="mt-0.5 text-[10px] text-slate-600">
                      {m.current.toLocaleString()} {m.unit}
                    </p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
