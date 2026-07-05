"use client";

import { Swords, Target, CalendarClock, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RankCard as RankCardData } from "@/features/rankings/api/ranking-api";
import { RankBadge } from "./rank-badge";
import { AnimatedNumber } from "./live/animated-number";

/**
 * Tier ランクカード（チーム/プレイヤー完全共通 / ADR-0016）。
 * Achievement Card の横に配置できる自己完結コンポーネント。データ取得はしない。
 */
export function RankCard({ card, heading = "RANK" }: { card: RankCardData; heading?: string }) {
  const name = card.team_name ?? card.in_game_name ?? "";
  const ranked = card.rank != null;

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-bold text-white">
          <Swords className="h-4 w-4" style={{ color: card.tier_color }} />
          {heading}
        </h2>
        <span className="text-xs text-slate-500">
          {ranked ? (
            <>Global <span className="font-black text-white">#{card.rank}</span> <span className="text-slate-600">/ {card.total_ranked}</span></>
          ) : "未ランク"}
        </span>
      </div>

      <div className="flex items-center gap-5">
        {/* Tier リング + Glow + Progress */}
        <RankBadge variant="ring" ringLarge glow tierKey={card.tier_key} label={card.tier_label} color={card.tier_color} progress={card.progress} />

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-slate-400">{name}</p>
          <p className="text-3xl font-black tabular-nums text-white">
            <AnimatedNumber value={card.rp} durationMs={1100} />
            <span className="ml-1 text-xs font-bold text-slate-500">RP</span>
          </p>

          {/* 次 Tier までの進捗 */}
          <div className="mt-2">
            <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
              <span>次のTier</span>
              <span style={{ color: card.tier_color }}>{card.next_tier_label ?? "MAX"}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full" style={{ width: `${Math.round(card.progress * 100)}%`, backgroundColor: card.tier_color }} />
            </div>
          </div>
        </div>
      </div>

      {/* サマリ */}
      <div className="mt-4 grid grid-cols-3 gap-3 border-t border-white/8 pt-4 text-center">
        <Stat icon={CalendarClock} label="今季 RP" value={card.current_season_rp.toLocaleString()} />
        <Stat icon={Target} label="勝率" value={`${(card.win_rate * 100).toFixed(0)}%`} />
        <Stat icon={Star} label="Best Tier" value={card.best_season_tier ?? "—"} color={card.best_season_tier_color ?? undefined} />
      </div>

      {/* Season History */}
      {card.seasons.length > 0 && (
        <div className="mt-4 border-t border-white/8 pt-4">
          <h3 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-500">Season History</h3>
          <ul className="space-y-1.5">
            {card.seasons.map((s) => (
              <li key={s.key} className="flex items-center gap-3 text-sm">
                <span className="w-20 flex-shrink-0 text-xs text-slate-500">{s.label}</span>
                <RankBadge variant="compact" label={s.tier_label} color={s.tier_color} />
                <span className="ml-auto tabular-nums font-bold text-white">{s.rp.toLocaleString()} RP</span>
                <span className="w-12 flex-shrink-0 text-right text-xs text-slate-500">{s.rank != null ? `#${s.rank}` : "—"}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Stat({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color?: string }) {
  return (
    <div>
      <Icon className="mx-auto mb-1 h-4 w-4 text-slate-500" />
      <p className="text-sm font-black text-white" style={color ? { color } : undefined}>{value}</p>
      <p className="text-[10px] text-slate-500">{label}</p>
    </div>
  );
}
