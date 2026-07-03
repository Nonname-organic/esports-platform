import { cn } from "@/lib/utils";
import { fmtNum, fmtPct, wrColor, DASH } from "./stat-format";

export interface MapCardData {
  map: string;
  games: number;
  win_rate: number;
  acs: number | null;
  kd: number | null;
  kda: number | null;
  attack_win_rate?: number | null;
  defense_win_rate?: number | null;
  first_kill_rate?: number | null;
}

/** Mapカード（Maps タブのグリッド要素） */
export function MapCard({ data }: { data: MapCardData }) {
  return (
    <div className="rounded-xl border border-white/8 bg-slate-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-white">{data.map}</p>
          <p className="text-xs text-slate-500">{data.games}試合</p>
        </div>
        <span className={cn("text-lg font-black tabular-nums", wrColor(data.win_rate))}>
          {fmtPct(data.win_rate, 0)}
        </span>
      </div>

      {/* Attack / Defense バー */}
      <div className="mb-3 space-y-1.5">
        <SideBar label="ATK" value={data.attack_win_rate} color="bg-red-500" />
        <SideBar label="DEF" value={data.defense_win_rate} color="bg-blue-500" />
      </div>

      <div className="grid grid-cols-4 gap-1.5 text-center">
        <Mini label="ACS" value={fmtNum(data.acs, 0)} />
        <Mini label="KD" value={fmtNum(data.kd, 2)} />
        <Mini label="KDA" value={fmtNum(data.kda, 2)} />
        <Mini label="FK%" value={data.first_kill_rate != null ? fmtPct(data.first_kill_rate, 0) : DASH} />
      </div>
    </div>
  );
}

function SideBar({ label, value, color }: { label: string; value: number | null | undefined; color: string }) {
  const pct = value != null ? Math.round(value * 100) : null;
  return (
    <div className="flex items-center gap-2">
      <span className="w-8 text-[10px] font-semibold text-slate-500">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        {pct != null && <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />}
      </div>
      <span className="w-9 text-right text-[10px] tabular-nums text-slate-400">{pct != null ? `${pct}%` : DASH}</span>
    </div>
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
