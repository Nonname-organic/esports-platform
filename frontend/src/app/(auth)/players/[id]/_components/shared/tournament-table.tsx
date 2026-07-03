import Link from "next/link";
import { cn } from "@/lib/utils";
import { DASH } from "./stat-format";

export interface TournamentRow {
  id: string;
  name: string;
  placement?: string | null;   // 順位（例: "優勝", "TOP4", "3位"）
  agent?: string | null;
  win_rate?: string | null;
  kda?: string | null;
  date?: string | null;
  href?: string;
}

/** 大会成績の一覧テーブル（Tournament / History で使用） */
export function TournamentTable({ rows }: { rows: TournamentRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900">
      <table className="w-full min-w-[560px] text-xs">
        <thead>
          <tr className="border-b border-white/10 text-slate-500">
            <th className="px-4 py-3 text-left font-medium">大会</th>
            <th className="px-3 py-3 text-center font-medium">順位</th>
            <th className="px-3 py-3 text-center font-medium">Agent</th>
            <th className="px-3 py-3 text-center font-medium">勝率</th>
            <th className="px-3 py-3 text-center font-medium">KDA</th>
            <th className="px-4 py-3 text-right font-medium">日付</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((r) => (
            <tr key={r.id} className="transition-colors hover:bg-white/3">
              <td className="px-4 py-3 font-medium text-white">
                {r.href ? <Link href={r.href} className="hover:text-brand-400">{r.name}</Link> : r.name}
              </td>
              <td className="px-3 py-3 text-center">
                {r.placement ? (
                  <span className={cn(
                    "inline-flex rounded-md px-2 py-0.5 text-[10px] font-bold",
                    r.placement.includes("優勝") ? "bg-yellow-500/10 text-yellow-400" :
                    r.placement.includes("TOP") ? "bg-brand-500/10 text-brand-400" : "bg-white/5 text-slate-400",
                  )}>{r.placement}</span>
                ) : DASH}
              </td>
              <td className="px-3 py-3 text-center text-slate-300">{r.agent ?? DASH}</td>
              <td className="px-3 py-3 text-center tabular-nums text-white">{r.win_rate ?? DASH}</td>
              <td className="px-3 py-3 text-center tabular-nums text-brand-400">{r.kda ?? DASH}</td>
              <td className="px-4 py-3 text-right text-slate-500">
                {r.date ? new Date(r.date).toLocaleDateString("ja-JP") : DASH}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
