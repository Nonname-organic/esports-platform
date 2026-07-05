"use client";

import { Activity, Swords, Flag, Clock } from "lucide-react";
import { useTournamentLive } from "@/features/tournament-live/hooks/use-tournament-live";
import { AnimatedNumber } from "@/components/live/animated-number";
import { LiveDot } from "@/components/live/live-dot";

/** Live Tournament Status: 進行率(Progress Ring) + 残り試合 + Current Round。 */
export function LiveStatusCard({ tournamentId, active }: { tournamentId: string; active: boolean }) {
  const { data } = useTournamentLive(tournamentId, active);
  if (!data || data.total_matches === 0) return null;

  const pct = Math.round(data.progress * 100);
  const dim = 96;
  const stroke = 8;
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 font-bold text-white">
        <Activity className="h-4 w-4 text-brand-400" /> LIVE STATUS
        {active && data.ongoing_matches > 0 && <LiveDot />}
      </h2>

      <div className="flex items-center gap-6">
        {/* Progress Ring */}
        <span className="relative inline-flex flex-shrink-0 items-center justify-center" style={{ width: dim, height: dim }}>
          <svg width={dim} height={dim} className="-rotate-90">
            <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
            <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="#3b82f6" strokeWidth={stroke}
              strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ * (1 - data.progress)}
              style={{ transition: "stroke-dashoffset 0.8s ease", filter: "drop-shadow(0 0 6px rgba(59,130,246,0.6))" }} />
          </svg>
          <span className="absolute text-center">
            <span className="block text-2xl font-black tabular-nums text-white"><AnimatedNumber value={pct} durationMs={900} />%</span>
            <span className="block text-[10px] text-slate-500">進行率</span>
          </span>
        </span>

        {/* Counts */}
        <div className="grid flex-1 grid-cols-3 gap-3">
          <Metric icon={Swords} color="text-red-400" label="残り試合" value={data.remaining_matches} />
          <Metric icon={Flag} color="text-green-400" label="消化" value={data.completed_matches} suffix={`/${data.total_matches}`} />
          <Metric icon={Clock} color="text-yellow-400" label="Round" value={data.current_round ?? 0} />
        </div>
      </div>
    </section>
  );
}

function Metric({ icon: Icon, color, label, value, suffix }: { icon: React.ElementType; color: string; label: string; value: number; suffix?: string }) {
  return (
    <div className="text-center">
      <Icon className={`mx-auto mb-1 h-4 w-4 ${color}`} />
      <p className="text-xl font-black tabular-nums text-white">
        <AnimatedNumber value={value} durationMs={800} />
        {suffix && <span className="text-xs font-normal text-slate-500">{suffix}</span>}
      </p>
      <p className="text-[10px] text-slate-500">{label}</p>
    </div>
  );
}
