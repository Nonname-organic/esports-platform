import Link from "next/link";
import { User, Shield, ExternalLink } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import type { Player, PlayerCareerStats } from "@/types/player";

const ROLE_LABEL: Record<string, string> = {
  player: "選手",
  coach: "コーチ",
  analyst: "アナリスト",
  manager: "マネージャー",
  substitute: "補欠",
};

interface PlayerHeaderProps {
  player: Player;
  stats: PlayerCareerStats;
}

export function PlayerHeader({ player, stats }: PlayerHeaderProps) {
  const winRatePct = (stats.win_rate * 100).toFixed(1);
  const hsRatePct = (stats.headshot_rate * 100).toFixed(1);

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
      {/* バナー */}
      <div className="h-24 bg-gradient-to-br from-brand-900/40 to-slate-950 relative">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(59,130,246,0.12),transparent_60%)]" />
      </div>

      <div className="px-6 pb-6">
        {/* アバター + 基本情報 */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          {/* アバター */}
          <div className="-mt-12 flex-shrink-0">
            <div className="h-20 w-20 overflow-hidden rounded-2xl border-4 border-slate-900 bg-slate-800 shadow-xl">
              {player.avatar_url ? (
                <img
                  src={player.avatar_url}
                  alt={player.display_name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <User className="h-8 w-8 text-slate-600" />
                </div>
              )}
            </div>
          </div>

          {/* 名前・所属 */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-bold", getGameColor(player.game))}>
                {player.game}
              </span>
              {player.role && (
                <span className="rounded-full bg-white/5 px-2.5 py-0.5 text-xs text-slate-400">
                  {ROLE_LABEL[player.role] ?? player.role}
                </span>
              )}
              {player.country && (
                <span className="text-xs text-slate-500">{player.country}</span>
              )}
            </div>
            <h1 className="mt-1 text-2xl font-black text-white">{player.display_name}</h1>
            {player.in_game_name && player.in_game_name !== player.display_name && (
              <p className="text-sm text-slate-500">
                IGN: <span className="text-slate-400">{player.in_game_name}</span>
              </p>
            )}
          </div>

          {/* 所属チーム */}
          {player.team_id && (
            <Link
              href={`/teams/${player.team_id}`}
              className="flex flex-shrink-0 items-center gap-2 rounded-xl border border-white/10 bg-white/3 px-4 py-2 hover:border-white/20 hover:bg-white/5 transition-colors"
            >
              <div className="h-8 w-8 overflow-hidden rounded-lg bg-slate-800 flex items-center justify-center">
                {player.team_logo_url ? (
                  <img src={player.team_logo_url} alt={player.team_name ?? ""} className="h-full w-full object-contain" />
                ) : (
                  <Shield className="h-4 w-4 text-slate-600" />
                )}
              </div>
              <div>
                <p className="text-sm font-bold text-white">{player.team_name ?? "Unknown"}</p>
                <p className="text-xs text-slate-500">[{player.team_tag}]</p>
              </div>
              <ExternalLink className="h-3.5 w-3.5 text-slate-600" />
            </Link>
          )}
        </div>

        {/* エージェント専門 */}
        {player.agent_specialty && player.agent_specialty.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {player.agent_specialty.map((agent) => (
              <span key={agent} className="rounded-lg bg-white/5 px-2.5 py-1 text-xs font-medium text-slate-300">
                {agent}
              </span>
            ))}
          </div>
        )}

        {/* キャリアスタッツ */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          <StatCard label="Rating" value={player.rating.toLocaleString()} color="text-brand-400" />
          <StatCard label="KDA" value={stats.avg_kda.toFixed(2)} />
          <StatCard label="勝率" value={`${winRatePct}%`} color={stats.win_rate >= 0.6 ? "text-green-400" : undefined} />
          <StatCard label="K/D/A" value={`${stats.avg_kills.toFixed(1)}/${stats.avg_deaths.toFixed(1)}/${stats.avg_assists.toFixed(1)}`} small />
          <StatCard label="HS率" value={`${hsRatePct}%`} />
          <StatCard label="試合数" value={stats.total_matches.toString()} />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
  small = false,
}: {
  label: string;
  value: string;
  color?: string;
  small?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/3 px-3 py-2.5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cn("mt-0.5 font-black leading-tight", small ? "text-sm" : "text-lg", color ?? "text-white")}>
        {value}
      </p>
    </div>
  );
}
