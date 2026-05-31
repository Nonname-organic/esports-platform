import { Shield, Radio, Clock, Calendar, ExternalLink } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import type { MatchDetail } from "@/types/match";

const STATUS_CONFIG = {
  scheduled: { label: "試合予定", className: "text-slate-400 bg-slate-400/10", dot: false },
  ongoing: { label: "LIVE", className: "text-red-400 bg-red-400/10", dot: true },
  completed: { label: "終了", className: "text-slate-500 bg-slate-500/10", dot: false },
  cancelled: { label: "中止", className: "text-gray-600 bg-gray-600/10", dot: false },
  forfeit: { label: "没収試合", className: "text-orange-400 bg-orange-400/10", dot: false },
  no_show: { label: "不戦敗", className: "text-orange-400 bg-orange-400/10", dot: false },
} as const;

interface MatchHeroProps {
  match: MatchDetail;
  team1Wins: number;
  team2Wins: number;
}

export function MatchHero({ match, team1Wins, team2Wins }: MatchHeroProps) {
  const cfg = STATUS_CONFIG[match.status] ?? STATUS_CONFIG.scheduled;
  const isCompleted = match.status === "completed";
  const winnerTeam = isCompleted && match.winner_id
    ? match.winner_id === match.team1?.id ? match.team1 : match.team2
    : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
      {/* 上部: ステータス + フォーマット */}
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold", cfg.className)}>
          {cfg.dot && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />}
          {cfg.label}
        </span>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-semibold text-white">
            {match.format}
          </span>
          {match.scheduled_at && !isCompleted && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDate(match.scheduled_at)}
            </span>
          )}
          {match.started_at && isCompleted && match.ended_at && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {Math.round((new Date(match.ended_at).getTime() - new Date(match.started_at).getTime()) / 60000)} 分
            </span>
          )}
        </div>
      </div>

      {/* メイン: チーム対戦 */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-6 px-6 py-8">
        {/* Team 1 */}
        <TeamDisplay
          team={match.team1}
          wins={team1Wins}
          isWinner={winnerTeam?.id === match.team1?.id}
          align="left"
        />

        {/* スコア */}
        <div className="text-center">
          <div className="text-5xl font-black tabular-nums text-white">
            {team1Wins}
            <span className="mx-3 text-slate-600">:</span>
            {team2Wins}
          </div>
          {match.status === "ongoing" && (
            <div className="mt-2 flex items-center justify-center gap-1.5 text-red-400">
              <Radio className="h-3.5 w-3.5 animate-pulse" />
              <span className="text-xs font-semibold">LIVE</span>
            </div>
          )}
          {isCompleted && winnerTeam && (
            <div className="mt-2 text-xs font-semibold text-yellow-400">
              🏆 {winnerTeam.name} 勝利
            </div>
          )}
        </div>

        {/* Team 2 */}
        <TeamDisplay
          team={match.team2}
          wins={team2Wins}
          isWinner={winnerTeam?.id === match.team2?.id}
          align="right"
        />
      </div>

      {/* 下部: 配信リンク */}
      {(match.stream_url || match.vod_url) && (
        <div className="flex items-center gap-3 border-t border-white/10 px-5 py-3">
          {match.stream_url && (
            <a
              href={match.stream_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <Radio className="h-3.5 w-3.5" />
              LIVE配信
            </a>
          )}
          {match.vod_url && (
            <a
              href={match.vod_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              VOD
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function TeamDisplay({
  team, wins, isWinner, align,
}: {
  team: MatchDetail["team1"];
  wins: number;
  isWinner: boolean;
  align: "left" | "right";
}) {
  return (
    <div className={cn("flex items-center gap-4", align === "right" && "flex-row-reverse")}>
      <div className={cn(
        "h-16 w-16 flex-shrink-0 overflow-hidden rounded-2xl border-2 bg-slate-800 flex items-center justify-center transition-all",
        isWinner ? "border-yellow-400/50 shadow-lg shadow-yellow-400/10" : "border-white/10",
      )}>
        {team?.logo_url ? (
          <img src={team.logo_url} alt={team.name} className="h-full w-full object-contain p-1" />
        ) : (
          <Shield className="h-8 w-8 text-slate-600" />
        )}
      </div>
      <div className={cn(align === "right" && "text-right")}>
        <p className={cn("text-xl font-black", isWinner ? "text-yellow-400" : "text-white")}>
          {team?.name ?? "TBD"}
        </p>
        <p className="text-xs text-slate-500">[{team?.tag ?? "???"}]</p>
      </div>
    </div>
  );
}
