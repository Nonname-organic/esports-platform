"use client";

import { TrendingUp } from "lucide-react";
import { useAnalyticsGrowth } from "@/features/analytics/hooks/use-analytics";

/** 月次成長推移 — シーンの健全性指標（完了大会 / 新規チーム / 新規ユーザー）。 */
export function GrowthSection() {
  const { data, isLoading } = useAnalyticsGrowth(12);
  const rows = data ?? [];
  const max = Math.max(...rows.map((r) => Math.max(r.tournaments, r.new_teams, r.new_users)), 1);

  const series = [
    { key: "tournaments" as const, label: "完了大会", color: "bg-brand-500" },
    { key: "new_teams" as const, label: "新規チーム", color: "bg-violet-500" },
    { key: "new_users" as const, label: "新規ユーザー", color: "bg-emerald-500" },
  ];

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-emerald-500/10 p-1.5">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">プラットフォーム成長推移</h2>
            <p className="text-xs text-slate-500">直近12ヶ月の開催・参加の伸び</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {series.map((s) => (
            <span key={s.key} className="flex items-center gap-1 text-[10px] text-slate-400">
              <span className={`h-2 w-2 rounded-sm ${s.color}`} />
              {s.label}
            </span>
          ))}
        </div>
      </div>

      <div className="px-5 py-4">
        {isLoading && <div className="h-48 animate-pulse rounded-xl bg-white/5" />}
        {!isLoading && rows.length > 0 && (
          <div className="flex h-48 items-end gap-1.5">
            {rows.map((r) => (
              <div key={r.month} className="group relative flex flex-1 flex-col items-center justify-end gap-px self-stretch">
                <div className="flex w-full flex-1 items-end justify-center gap-[2px]">
                  {series.map((s) => (
                    <div
                      key={s.key}
                      className={`w-1/4 rounded-t-sm ${s.color} opacity-80 transition-opacity group-hover:opacity-100`}
                      style={{ height: `${(r[s.key] / max) * 100}%`, minHeight: r[s.key] > 0 ? "3px" : "0" }}
                    />
                  ))}
                </div>
                <span className="text-[9px] text-slate-600">{r.month.slice(2).replace("-", "/")}</span>
                {/* hover tooltip */}
                <div className="pointer-events-none absolute bottom-full mb-1 hidden whitespace-nowrap rounded-lg border border-white/10 bg-slate-800 px-2 py-1 text-[10px] text-slate-200 group-hover:block">
                  {r.month}: 大会{r.tournaments} / チーム{r.new_teams} / ユーザー{r.new_users}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
