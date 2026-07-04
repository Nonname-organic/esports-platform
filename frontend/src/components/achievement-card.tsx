import { Trophy, Medal, Award, Target, Star, CalendarDays } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * 実績カード（共通・プレゼンテーション専用 / データ取得はしない）。
 * Team だけでなく将来 Player / Tournament の実績カードでも流用できるよう、
 * エンティティ非依存の正規化された props を受け取る。
 */

export interface AchievementCardTitle {
  placement: "champion" | "runner_up" | "top4" | string;
  label: string;          // 大会名など
  href?: string;          // 任意リンク（大会詳細等）
  date?: string | null;   // ISO8601
}

export interface AchievementCardProps {
  heading?: string;
  championships: number;
  runnerUps: number;
  top4: number;
  winRate: number;        // 0..1
  wins: number;
  losses: number;
  matches: number;
  tournaments: number;
  mvps: number;
  since?: string | null;  // ISO8601
  recentTitles: AchievementCardTitle[];
}

const PLACEMENT_META: Record<string, { label: string; cls: string }> = {
  champion: { label: "Champion", cls: "bg-yellow-500/15 text-yellow-400" },
  runner_up: { label: "Runner-up", cls: "bg-slate-300/10 text-slate-300" },
  top4: { label: "Top4", cls: "bg-amber-700/15 text-amber-500" },
};

function fmtDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("ja-JP", { year: "numeric", month: "short", day: "numeric" });
}

export function AchievementCard({
  heading = "Achievements",
  championships, runnerUps, top4, winRate, wins, losses, matches, tournaments, mvps, since, recentTitles,
}: AchievementCardProps) {
  const sinceYear = since ? new Date(since).getFullYear() : null;

  const tiles = [
    { icon: Trophy, color: "text-yellow-400", bg: "bg-yellow-500/10", label: "Championships", value: championships },
    { icon: Medal, color: "text-slate-300", bg: "bg-slate-300/10", label: "Runner-up", value: runnerUps },
    { icon: Award, color: "text-amber-500", bg: "bg-amber-700/15", label: "Top4", value: top4 },
    { icon: Target, color: "text-brand-400", bg: "bg-brand-500/10", label: "Match Win Rate", value: `${(winRate * 100).toFixed(1)}%` },
    { icon: Star, color: "text-purple-400", bg: "bg-purple-500/10", label: "MVP", value: mvps },
  ];

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-bold text-white">
          <Trophy className="h-4 w-4 text-yellow-400" />
          {heading}
        </h2>
        {sinceYear && (
          <span className="flex items-center gap-1.5 text-xs text-slate-500">
            <CalendarDays className="h-3.5 w-3.5" />
            Since {sinceYear}
          </span>
        )}
      </div>

      {/* スタッツタイル */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-xl border border-white/8 bg-white/3 p-3">
            <div className={cn("mb-2 inline-flex rounded-lg p-1.5", t.bg)}>
              <t.icon className={cn("h-4 w-4", t.color)} />
            </div>
            <p className="text-lg font-black text-white">{t.value}</p>
            <p className="text-[11px] leading-tight text-slate-500">{t.label}</p>
          </div>
        ))}
      </div>

      {/* サマリ行 */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>{wins}W / {losses}L（{matches} 試合）</span>
        <span>参加大会 {tournaments}</span>
      </div>

      {/* Recent Titles */}
      {recentTitles.length > 0 && (
        <div className="mt-5 border-t border-white/8 pt-4">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Recent Titles</h3>
          <ul className="space-y-1.5">
            {recentTitles.map((t, i) => {
              const meta = PLACEMENT_META[t.placement] ?? { label: t.placement, cls: "bg-white/5 text-slate-300" };
              const row = (
                <>
                  <span className={cn("flex-shrink-0 rounded-md px-2 py-0.5 text-[11px] font-bold", meta.cls)}>
                    {meta.label}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm text-white">{t.label}</span>
                  {t.date && <span className="flex-shrink-0 text-xs text-slate-500">{fmtDate(t.date)}</span>}
                </>
              );
              return (
                <li key={`${t.placement}-${i}`} className="flex items-center gap-2.5">
                  {t.href ? (
                    <a href={t.href} className="flex min-w-0 flex-1 items-center gap-2.5 hover:opacity-80 transition-opacity">
                      {row}
                    </a>
                  ) : row}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
