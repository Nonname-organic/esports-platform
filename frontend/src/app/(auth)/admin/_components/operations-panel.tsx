"use client";

import { CalendarCheck, ClipboardList, BarChart2, Swords, PlayCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AdminOperations } from "@/types/admin";

interface OpMetricProps {
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  label: string;
  value: string;
  sub?: string;
  alert?: boolean;
}

function OpMetric({ icon: Icon, iconColor, iconBg, label, value, sub, alert }: OpMetricProps) {
  return (
    <div className={cn(
      "flex items-start gap-3 rounded-xl border p-4 transition-colors",
      alert ? "border-yellow-500/30 bg-yellow-500/5" : "border-white/8 bg-slate-900",
    )}>
      <div className={cn("mt-0.5 rounded-lg p-1.5", iconBg)}>
        <Icon className={cn("h-4 w-4", iconColor)} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-500">{label}</p>
        <p className={cn("mt-0.5 text-xl font-black", alert ? "text-yellow-400" : "text-white")}>{value}</p>
        {sub && <p className="mt-0.5 text-[10px] text-slate-600">{sub}</p>}
      </div>
    </div>
  );
}

interface OperationsPanelProps {
  ops: AdminOperations;
}

export function OperationsPanel({ ops }: OperationsPanelProps) {
  const participationPct = (ops.avg_participation_rate * 100).toFixed(1);
  const cancelledPct = (ops.cancelled_rate * 100).toFixed(1);
  const hasPending = ops.pending_registrations > 0;

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900/50">
      <div className="border-b border-white/10 px-5 py-4">
        <h2 className="text-sm font-bold text-white">運営指標</h2>
        <p className="text-xs text-slate-500">今月・現在の運営状況</p>
      </div>
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3">
        <OpMetric
          icon={CalendarCheck}
          iconBg="bg-brand-500/10"
          iconColor="text-brand-400"
          label="今月開催"
          value={`${ops.tournaments_this_month}件`}
          sub="大会"
        />
        <OpMetric
          icon={ClipboardList}
          iconBg={hasPending ? "bg-yellow-500/10" : "bg-slate-700/50"}
          iconColor={hasPending ? "text-yellow-400" : "text-slate-500"}
          label="申請数（承認待ち）"
          value={`${ops.pending_registrations}件`}
          alert={hasPending}
        />
        <OpMetric
          icon={BarChart2}
          iconBg="bg-green-500/10"
          iconColor="text-green-400"
          label="参加率（平均）"
          value={`${participationPct}%`}
          sub="登録/定員"
        />
        <OpMetric
          icon={Swords}
          iconBg="bg-purple-500/10"
          iconColor="text-purple-400"
          label="本日完了試合"
          value={`${ops.completed_matches_today}試合`}
        />
        <OpMetric
          icon={PlayCircle}
          iconBg="bg-red-500/10"
          iconColor="text-red-400"
          label="開催中大会"
          value={`${ops.ongoing_tournaments}件`}
        />
        <OpMetric
          icon={XCircle}
          iconBg="bg-slate-700/50"
          iconColor="text-slate-500"
          label="キャンセル率"
          value={`${cancelledPct}%`}
          sub="今月"
        />
      </div>
    </section>
  );
}
