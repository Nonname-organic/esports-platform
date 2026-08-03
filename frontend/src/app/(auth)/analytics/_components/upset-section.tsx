"use client";

import { Swords } from "lucide-react";
import { useAnalyticsUpsets } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";

/**
 * ジャイアントキリング（番狂わせ）統計 — ブラケット結果 × 競技ランキングの掛け合わせ。
 * RP下位チームがRP上位チームを撃破した試合を集計する、大会主催プラットフォーム限定のメタ。
 */
export function UpsetSection() {
  const { game } = useAnalyticsFilterStore();
  const { data, isLoading } = useAnalyticsUpsets({ game });

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-amber-500/10 p-1.5">
            <Swords className="h-4 w-4 text-amber-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">ジャイアントキリング</h2>
            <p className="text-xs text-slate-500">RP格上を撃破した番狂わせ — AXELIA大会限定メタ</p>
          </div>
        </div>
        {data && data.ranked_matches > 0 && (
          <div className="text-right">
            <p className="text-lg font-black tabular-nums text-amber-400">
              {(data.upset_rate * 100).toFixed(1)}%
            </p>
            <p className="text-[10px] text-slate-500">番狂わせ率 ({data.upsets}/{data.ranked_matches}試合)</p>
          </div>
        )}
      </div>

      <div className="px-5 py-4">
        {isLoading && <div className="h-56 animate-pulse rounded-xl bg-white/5" />}
        {!isLoading && (!data || data.giant_killers.length === 0) && (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-slate-500">番狂わせはまだ起きていません</p>
          </div>
        )}
        {!isLoading && data && data.giant_killers.length > 0 && (
          <div className="space-y-4">
            {/* ジャイアントキラー・ランキング */}
            <div>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                トップ・ジャイアントキラー
              </p>
              <ul className="space-y-1.5">
                {data.giant_killers.slice(0, 5).map((k, i) => (
                  <li
                    key={k.team_id}
                    className="flex items-center gap-3 rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2 text-xs"
                  >
                    <span className="w-5 text-center font-black text-amber-400">{i + 1}</span>
                    <span className="min-w-0 flex-1 truncate font-bold text-white">
                      {k.team_name} <span className="text-slate-500">[{k.team_tag}]</span>
                    </span>
                    <span className="font-bold tabular-nums text-amber-300">⚔️ {k.upsets}回</span>
                    {k.biggest_victim_name && (
                      <span className="hidden text-[10px] text-slate-500 sm:inline">
                        最大: RP差{k.biggest_gap} ({k.biggest_victim_name}戦)
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* 直近の番狂わせ */}
            {data.recent_upsets.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  直近の番狂わせ
                </p>
                <ul className="space-y-1 text-[11px] text-slate-400">
                  {data.recent_upsets.slice(0, 4).map((u, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="font-bold text-white">{u.winner_name}</span>
                      <span className="text-slate-600">が格上</span>
                      <span className="font-semibold text-slate-300">{u.loser_name}</span>
                      <span className="text-slate-600">を撃破</span>
                      <span className="font-bold text-amber-400">(RP差{u.rp_gap})</span>
                      <span className="ml-auto hidden truncate text-slate-600 sm:inline">{u.tournament_name}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
