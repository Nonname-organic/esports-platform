"use client";

import { Ban } from "lucide-react";
import { useAnalyticsVeto } from "@/features/analytics/hooks/use-analytics";
import { useAnalyticsFilterStore } from "@/store/analytics-filter-store";

/**
 * マップ BAN/PICK 率 — 大会の ban_picks に基づく AXELIA 限定メタ
 * （ランクマッチ統計サイトには存在しない、大会主催プラットフォームだけのデータ）。
 */
export function VetoSection() {
  const { game, tournamentId } = useAnalyticsFilterStore();
  const { data, isLoading } = useAnalyticsVeto({ game, tournamentId: tournamentId || undefined });
  const rows = data ?? [];
  const maxBan = Math.max(...rows.map((r) => r.ban_rate), 0.0001);
  const maxPick = Math.max(...rows.map((r) => r.pick_rate), 0.0001);

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
        <div className="rounded-lg bg-rose-500/10 p-1.5">
          <Ban className="h-4 w-4 text-rose-400" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-white">マップ BAN / PICK 率</h2>
          <p className="text-xs text-slate-500">大会のBAN/PICKフェーズ集計 — AXELIA大会限定メタ</p>
        </div>
      </div>

      <div className="px-5 py-4">
        {isLoading && <div className="h-56 animate-pulse rounded-xl bg-white/5" />}
        {!isLoading && rows.length === 0 && (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-slate-500">BAN/PICKデータがまだありません</p>
          </div>
        )}
        {!isLoading && rows.length > 0 && (
          <div className="space-y-2.5">
            {rows.map((r) => (
              <div key={r.map_name} className="grid grid-cols-[6rem_1fr_1fr] items-center gap-3 text-xs">
                <span className="truncate font-bold text-white">{r.map_name}</span>
                <div>
                  <div className="mb-0.5 flex justify-between text-[10px] text-slate-500">
                    <span>BAN {(r.ban_rate * 100).toFixed(1)}%</span>
                    <span>{r.bans}回</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/5">
                    <div className="h-full rounded-full bg-rose-500/70" style={{ width: `${(r.ban_rate / maxBan) * 100}%` }} />
                  </div>
                </div>
                <div>
                  <div className="mb-0.5 flex justify-between text-[10px] text-slate-500">
                    <span>PICK {(r.pick_rate * 100).toFixed(1)}%</span>
                    <span>{r.picks}回</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/5">
                    <div className="h-full rounded-full bg-emerald-500/70" style={{ width: `${(r.pick_rate / maxPick) * 100}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
