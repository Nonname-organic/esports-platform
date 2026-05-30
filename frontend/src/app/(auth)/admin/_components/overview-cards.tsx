"use client";

import { Trophy, Users, Swords, User2, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AdminOverview } from "@/types/admin";

function TrendBadge({ value }: { value: number }) {
  const isPos = value >= 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
        isPos ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400",
      )}
    >
      {isPos ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
      {isPos ? "+" : ""}{value.toFixed(1)}%
    </span>
  );
}

interface KpiCardProps {
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  label: string;
  value: string | number;
  sub?: string;
  trend?: number;
  highlight?: boolean;
  formatter?: (v: number) => string;
}

function KpiCard({ icon: Icon, iconBg, iconColor, label, value, sub, trend, highlight }: KpiCardProps) {
  return (
    <div
      className={cn(
        "group rounded-xl border bg-slate-900 p-4 transition-all hover:border-white/20",
        highlight ? "border-brand-500/30" : "border-white/8",
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className={cn("rounded-lg p-1.5", iconBg)}>
          <Icon className={cn("h-4 w-4", iconColor)} />
        </div>
        {trend !== undefined && <TrendBadge value={trend} />}
      </div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cn("mt-0.5 text-2xl font-black", highlight ? "text-brand-400" : "text-white")}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
      {sub && <p className="mt-0.5 text-[10px] text-slate-600">{sub}</p>}
    </div>
  );
}

interface OverviewCardsProps {
  overview: AdminOverview;
}

export function OverviewCards({ overview }: OverviewCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-4 xl:grid-cols-4">
      <KpiCard
        icon={Users}
        iconBg="bg-brand-500/10"
        iconColor="text-brand-400"
        label="MAU"
        value={overview.mau.toLocaleString()}
        sub="月間アクティブユーザー"
        trend={overview.mau_trend}
        highlight
      />
      <KpiCard
        icon={User2}
        iconBg="bg-green-500/10"
        iconColor="text-green-400"
        label="DAU"
        value={overview.dau.toLocaleString()}
        sub="日間アクティブユーザー"
        trend={overview.dau_trend}
      />
      <KpiCard
        icon={Trophy}
        iconBg="bg-yellow-500/10"
        iconColor="text-yellow-400"
        label="総大会数"
        value={overview.total_tournaments.toLocaleString()}
      />
      <KpiCard
        icon={Swords}
        iconBg="bg-purple-500/10"
        iconColor="text-purple-400"
        label="総試合数"
        value={overview.total_matches.toLocaleString()}
      />
      <KpiCard
        icon={Users}
        iconBg="bg-cyan-500/10"
        iconColor="text-cyan-400"
        label="総チーム数"
        value={overview.total_teams.toLocaleString()}
      />
      <KpiCard
        icon={User2}
        iconBg="bg-pink-500/10"
        iconColor="text-pink-400"
        label="総プレイヤー数"
        value={overview.total_players.toLocaleString()}
      />
    </div>
  );
}
