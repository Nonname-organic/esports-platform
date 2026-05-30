"use client";

import { Map } from "lucide-react";
import { useAnalyticsWinRate } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";
import { MapWinRateChart } from "@/features/analytics/components/analytics-dashboard";

function Skeleton() {
  return <div className="h-72 animate-pulse rounded-xl bg-white/5" />;
}

export function MapSection() {
  const { game, tournamentId, dateFrom, dateTo } = useAnalyticsFilterStore();

  const { data, isLoading } = useAnalyticsWinRate({
    game,
    tournamentId: tournamentId || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  });

  const mapData = data?.by_map ?? [];

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
        <div className="rounded-lg bg-orange-500/10 p-1.5">
          <Map className="h-4 w-4 text-orange-400" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-white">MAP別勝率</h2>
          <p className="text-xs text-slate-500">攻撃側 / 守備側 勝率比較</p>
        </div>
      </div>

      <div className="px-5 py-4">
        {isLoading && <Skeleton />}
        {!isLoading && mapData.length === 0 && (
          <div className="flex h-48 items-center justify-center">
            <p className="text-sm text-slate-500">MAPデータがありません</p>
          </div>
        )}
        {!isLoading && mapData.length > 0 && (
          <>
            <MapWinRateChart data={mapData} />
            {/* MAP詳細テーブル */}
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/8 text-slate-500">
                    <th className="pb-2 text-left font-medium">MAP</th>
                    <th className="pb-2 text-center font-medium">試合数</th>
                    <th className="pb-2 text-center font-medium">攻撃側勝率</th>
                    <th className="pb-2 text-center font-medium">守備側勝率</th>
                    <th className="pb-2 text-center font-medium">平均時間</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[...mapData]
                    .sort((a, b) => b.total_games - a.total_games)
                    .map((m) => {
                      const atkPct = Math.round(m.attack_win_rate * 100);
                      const defPct = 100 - atkPct;
                      const dur = m.avg_duration_seconds
                        ? `${Math.floor(m.avg_duration_seconds / 60)}分`
                        : "—";
                      return (
                        <tr key={m.map_id} className="hover:bg-white/3 transition-colors">
                          <td className="py-2 font-semibold text-slate-300">{m.map_name || m.map_id}</td>
                          <td className="py-2 text-center text-slate-400">{m.total_games}</td>
                          <td className="py-2 text-center">
                            <span className={atkPct >= 55 ? "text-red-400 font-semibold" : atkPct >= 45 ? "text-white" : "text-slate-400"}>
                              {atkPct}%
                            </span>
                          </td>
                          <td className="py-2 text-center">
                            <span className={defPct >= 55 ? "text-brand-400 font-semibold" : defPct >= 45 ? "text-white" : "text-slate-400"}>
                              {defPct}%
                            </span>
                          </td>
                          <td className="py-2 text-center text-slate-400">{dur}</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
