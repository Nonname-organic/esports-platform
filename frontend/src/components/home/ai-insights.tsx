"use client";

import { Sparkles, DoorOpen, Zap, Coins, Users } from "lucide-react";
import type { HomeInsight } from "@/features/home/api/home-api";

const ICONS: Record<string, React.ElementType> = { door: DoorOpen, zap: Zap, coins: Coins, users: Users };

/** AI Insights: 実数から生成した規則ベースの気づき（毎日更新想定）。 */
export function AiInsights({ insights }: { insights: HomeInsight[] }) {
  if (!insights || insights.length === 0) return null;
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-3 flex items-center gap-2 font-bold text-white">
        <Sparkles className="h-4 w-4 text-purple-400" /> AI Insights
      </h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {insights.map((it, i) => {
          const Icon = ICONS[it.icon] ?? Sparkles;
          return (
            <div key={i} className="flex items-center gap-2.5 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
              <Icon className="h-4 w-4 flex-shrink-0 text-brand-400" />
              <span className="text-sm text-slate-300">{it.text}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
