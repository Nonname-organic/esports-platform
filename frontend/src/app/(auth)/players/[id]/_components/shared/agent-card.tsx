import { cn } from "@/lib/utils";
import { fmtNum, fmtPct, wrColor } from "./stat-format";

export interface AgentCardData {
  agent: string;
  games: number;
  win_rate: number;
  pick_rate?: number | null;
  acs: number | null;
  kd: number | null;
  kda: number | null;
  hs_rate?: number | null;
  mvp_rate?: number | null;
  avg_placement?: number | null;
}

/** Agentカード（Agents タブのグリッド要素）。クリックでAgent詳細へ */
export function AgentCard({ data, onClick }: { data: AgentCardData; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col rounded-xl border border-white/8 bg-slate-900 p-4 text-left transition-colors hover:border-brand-500/40"
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800 text-sm font-black text-slate-400">
          {data.agent.slice(0, 2).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">{data.agent}</p>
          <p className="text-xs text-slate-500">
            {data.games}試合{data.pick_rate != null ? ` · Pick ${fmtPct(data.pick_rate, 0)}` : ""}
          </p>
        </div>
        <span className={cn("ml-auto text-sm font-black tabular-nums", wrColor(data.win_rate))}>
          {fmtPct(data.win_rate, 0)}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-1.5 text-center">
        <Mini label="ACS" value={fmtNum(data.acs, 0)} />
        <Mini label="KD" value={fmtNum(data.kd, 2)} />
        <Mini label="KDA" value={fmtNum(data.kda, 2)} />
        <Mini label="HS%" value={data.hs_rate != null ? fmtPct(data.hs_rate, 0) : "—"} />
      </div>
    </button>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/3 py-1.5">
      <p className="text-xs font-bold text-white tabular-nums">{value}</p>
      <p className="text-[9px] text-slate-600">{label}</p>
    </div>
  );
}
