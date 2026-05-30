import { Shield, Globe, Twitter, Twitch } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import type { Team, TeamStats } from "@/types/team";

const ROLE_BADGE: Record<string, string> = {
  player: "bg-brand-500/10 text-brand-400",
  coach: "bg-yellow-500/10 text-yellow-400",
  analyst: "bg-purple-500/10 text-purple-400",
  manager: "bg-green-500/10 text-green-400",
  substitute: "bg-slate-500/10 text-slate-400",
};

interface TeamHeaderProps {
  team: Team;
  stats: TeamStats;
}

export function TeamHeader({ team, stats }: TeamHeaderProps) {
  const winRatePct = (stats.win_rate * 100).toFixed(1);

  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
      {/* バナー */}
      <div className="relative h-36 overflow-hidden bg-gradient-to-br from-slate-800 to-slate-950">
        {team.banner_url ? (
          <img src={team.banner_url} alt="" className="h-full w-full object-cover opacity-40" />
        ) : (
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(59,130,246,0.15),transparent_60%)]" />
        )}
      </div>

      <div className="px-6 pb-6">
        {/* ロゴ + 基本情報 */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="-mt-10 flex-shrink-0">
            <div className="h-20 w-20 overflow-hidden rounded-2xl border-4 border-slate-900 bg-slate-800 shadow-xl">
              {team.logo_url ? (
                <img src={team.logo_url} alt={team.name} className="h-full w-full object-contain p-1" />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <Shield className="h-8 w-8 text-slate-600" />
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-bold", getGameColor(team.game))}>
                {team.game}
              </span>
              {team.region && (
                <span className="rounded-full bg-white/5 px-2.5 py-0.5 text-xs text-slate-400">
                  {team.region}
                </span>
              )}
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <h1 className="text-2xl font-black text-white">{team.name}</h1>
              <span className="text-sm font-semibold text-slate-500">[{team.tag}]</span>
            </div>
            {team.description && (
              <p className="mt-1 line-clamp-2 text-sm text-slate-400">{team.description}</p>
            )}
          </div>

          {/* ソーシャルリンク */}
          {team.social_links && (
            <div className="flex items-center gap-2 flex-shrink-0">
              {team.social_links.twitter && (
                <a
                  href={`https://twitter.com/${team.social_links.twitter}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-white/10 p-2 text-slate-400 hover:text-white transition-colors"
                  aria-label="Twitter"
                >
                  <Twitter className="h-4 w-4" />
                </a>
              )}
              {team.social_links.twitch && (
                <a
                  href={`https://twitch.tv/${team.social_links.twitch}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-white/10 p-2 text-slate-400 hover:text-purple-400 transition-colors"
                  aria-label="Twitch"
                >
                  <Twitch className="h-4 w-4" />
                </a>
              )}
              {team.social_links.website && (
                <a
                  href={team.social_links.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-white/10 p-2 text-slate-400 hover:text-white transition-colors"
                  aria-label="Website"
                >
                  <Globe className="h-4 w-4" />
                </a>
              )}
            </div>
          )}
        </div>

        {/* スタッツ行 */}
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="勝率" value={`${winRatePct}%`} highlight={stats.win_rate >= 0.6} />
          <StatCard label="レーティング" value={stats.rating.toLocaleString()} />
          <StatCard label="勝 / 敗" value={`${stats.wins}W ${stats.losses}L`} />
          <StatCard label="大会優勝" value={`${stats.tournaments_won} / ${stats.tournaments_played}`} />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/3 px-4 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cn("mt-0.5 text-lg font-black", highlight ? "text-brand-400" : "text-white")}>
        {value}
      </p>
    </div>
  );
}
