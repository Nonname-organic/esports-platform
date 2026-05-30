import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";

const STATUS_CONFIG = {
  scheduled: { label: "予定", className: "text-slate-400 bg-slate-400/10" },
  ongoing: { label: "LIVE", className: "text-red-400 bg-red-400/10", pulse: true },
  completed: { label: "終了", className: "text-slate-500 bg-slate-500/10" },
  cancelled: { label: "中止", className: "text-gray-600 bg-gray-600/10" },
  forfeit: { label: "没収", className: "text-orange-400 bg-orange-400/10" },
  no_show: { label: "不戦", className: "text-orange-400 bg-orange-400/10" },
} as const;

interface MatchHeaderProps {
  match: MatchDetail;
}

export function MatchHeader({ match }: MatchHeaderProps) {
  const cfg = STATUS_CONFIG[match.status] ?? STATUS_CONFIG.scheduled;

  // ゲーム勝利数集計
  const team1Wins = match.games.filter((g) => g.winner_id === match.team1?.id).length;
  const team2Wins = match.games.filter((g) => g.winner_id === match.team2?.id).length;

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900 p-6">
      {/* ステータス + フォーマット */}
      <div className="mb-4 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold",
            cfg.className,
          )}
        >
          {"pulse" in cfg && cfg.pulse && (
            <span className="h-2 w-2 animate-pulse rounded-full bg-red-400" />
          )}
          {cfg.label}
        </span>
        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm font-bold text-white">
          {match.format}
        </span>
      </div>

      {/* 対戦表示 */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-6">
        <TeamDisplay team={match.team1} score={team1Wins} align="left" />

        {/* スコア */}
        <div className="text-center">
          <p className="text-4xl font-black tabular-nums text-white">
            {team1Wins}
            <span className="mx-2 text-slate-600">–</span>
            {team2Wins}
          </p>
          <p className="mt-1 text-xs text-slate-500">Round {match.round_number}</p>
        </div>

        <TeamDisplay team={match.team2} score={team2Wins} align="right" />
      </div>
    </div>
  );
}

function TeamDisplay({
  team,
  score,
  align,
}: {
  team: MatchDetail["team1"];
  score: number;
  align: "left" | "right";
}) {
  return (
    <div className={cn("flex items-center gap-3", align === "right" && "flex-row-reverse")}>
      <div className="h-14 w-14 flex-shrink-0 overflow-hidden rounded-xl border border-white/10 bg-slate-800 flex items-center justify-center">
        {team?.logo_url ? (
          <img src={team.logo_url} alt={team.name} className="h-full w-full object-contain p-1" />
        ) : (
          <Shield className="h-6 w-6 text-slate-600" />
        )}
      </div>
      <div className={cn(align === "right" && "text-right")}>
        <p className="text-lg font-black text-white">{team?.name ?? "TBD"}</p>
        <p className="text-xs text-slate-500">[{team?.tag ?? "???"}]</p>
      </div>
    </div>
  );
}
