import { cn } from "@/lib/utils";
import { fmtNum, fmtPct, DASH } from "./stat-format";

export interface MatchRow {
  id: string;
  agent: string | null;
  map_name: string | null;
  won: boolean | null;
  score?: string | null;
  kills: number;
  deaths: number;
  assists: number;
  kd: number | null;
  kda: number | null;
  acs: number | null;
  adr?: number | null;
  hs_rate?: number | null;
  played_at: string | null;
  onClick?: () => void;
}

/** Matches タブ / Competitive の試合一覧テーブル（レスポンシブ横スクロール） */
export function MatchTable({ rows }: { rows: MatchRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900">
      <table className="w-full min-w-[640px] text-xs">
        <thead>
          <tr className="border-b border-white/10 text-slate-500">
            <th className="px-4 py-3 text-left font-medium">結果</th>
            <th className="px-3 py-3 text-left font-medium">Map</th>
            <th className="px-3 py-3 text-left font-medium">Agent</th>
            <th className="px-3 py-3 text-center font-medium">K/D/A</th>
            <th className="px-3 py-3 text-center font-medium">KD</th>
            <th className="px-3 py-3 text-center font-medium">KDA</th>
            <th className="px-3 py-3 text-center font-medium">ACS</th>
            <th className="px-3 py-3 text-center font-medium">HS%</th>
            <th className="px-4 py-3 text-right font-medium">日時</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((m) => (
            <tr
              key={m.id}
              onClick={m.onClick}
              className={cn("transition-colors", m.onClick && "cursor-pointer hover:bg-white/3")}
            >
              <td className="px-4 py-3">
                <span
                  className={cn(
                    "inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold",
                    m.won === true ? "bg-green-500/10 text-green-400" :
                    m.won === false ? "bg-red-500/10 text-red-400" : "bg-white/5 text-slate-500",
                  )}
                >
                  {m.won === true ? "WIN" : m.won === false ? "LOSS" : DASH}
                  {m.score ? ` ${m.score}` : ""}
                </span>
              </td>
              <td className="px-3 py-3 text-slate-400">{m.map_name ?? DASH}</td>
              <td className="px-3 py-3 font-medium text-white">{m.agent ?? DASH}</td>
              <td className="px-3 py-3 text-center tabular-nums">
                <span className="text-green-400">{m.kills}</span>
                <span className="text-slate-600">/</span>
                <span className="text-red-400">{m.deaths}</span>
                <span className="text-slate-600">/</span>
                <span className="text-blue-400">{m.assists}</span>
              </td>
              <td className="px-3 py-3 text-center tabular-nums text-slate-300">{fmtNum(m.kd, 2)}</td>
              <td className="px-3 py-3 text-center tabular-nums font-semibold text-white">{fmtNum(m.kda, 2)}</td>
              <td className="px-3 py-3 text-center tabular-nums font-bold text-white">{fmtNum(m.acs, 0)}</td>
              <td className="px-3 py-3 text-center tabular-nums text-slate-400">
                {m.hs_rate != null ? fmtPct(m.hs_rate, 0) : DASH}
              </td>
              <td className="px-4 py-3 text-right text-slate-500">
                {m.played_at ? new Date(m.played_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" }) : DASH}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
