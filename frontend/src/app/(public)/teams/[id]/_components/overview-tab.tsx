import { Trophy, TrendingUp, Zap, Award } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TeamStats, Team } from "@/types/team";

interface OverviewTabProps {
  team: Team;
  stats: TeamStats;
}

function StreakBadge({ streak }: { streak: number }) {
  if (streak === 0) return null;
  const isWin = streak > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        isWin ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400",
      )}
    >
      <Zap className="h-3 w-3" />
      {isWin ? `${streak}連勝中` : `${Math.abs(streak)}連敗中`}
    </span>
  );
}

export function OverviewTab({ team, stats }: OverviewTabProps) {
  const gameWinRatePct = (stats.game_win_rate * 100).toFixed(1);
  const winRatePct = (stats.win_rate * 100).toFixed(1);

  return (
    <div className="space-y-6 pt-6">
      {/* ストリーク + ハイライト */}
      <div className="flex flex-wrap items-center gap-3">
        <StreakBadge streak={stats.current_streak} />
        {stats.best_streak > 0 && (
          <span className="text-xs text-slate-500">
            ベストストリーク: <span className="text-white font-semibold">{stats.best_streak}連勝</span>
          </span>
        )}
        {stats.peak_rating > 0 && (
          <span className="text-xs text-slate-500">
            最高レーティング: <span className="text-yellow-400 font-semibold">{stats.peak_rating.toLocaleString()}</span>
          </span>
        )}
      </div>

      {/* 詳細スタッツグリッド */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <DetailCard
          icon={Trophy}
          iconColor="text-brand-400"
          iconBg="bg-brand-500/10"
          label="マッチ成績"
          main={`${stats.wins}W / ${stats.losses}L`}
          sub={`${stats.total_matches} 試合`}
        />
        <DetailCard
          icon={TrendingUp}
          iconColor="text-green-400"
          iconBg="bg-green-500/10"
          label="マッチ勝率"
          main={`${winRatePct}%`}
          sub={`ゲーム勝率 ${gameWinRatePct}%`}
        />
        <DetailCard
          icon={Award}
          iconColor="text-yellow-400"
          iconBg="bg-yellow-500/10"
          label="大会成績"
          main={`${stats.tournaments_won}優勝`}
          sub={`${stats.tournaments_played} 大会参加`}
        />
      </div>

      {/* ゲーム勝率バー */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-bold text-white">ゲーム勝率内訳</h2>
        <div className="space-y-3">
          <WinLossBar
            label="マッチ"
            wins={stats.wins}
            losses={stats.losses}
            winColor="bg-brand-500"
          />
          <WinLossBar
            label="ゲーム"
            wins={stats.game_wins}
            losses={stats.game_losses}
            winColor="bg-green-500"
          />
        </div>
      </section>

      {/* 設立情報 */}
      {(team.founded_at || team.country || team.region) && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-bold text-white">チーム情報</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {team.founded_at && (
              <div>
                <dt className="text-slate-500">設立</dt>
                <dd className="mt-0.5 font-semibold text-white">
                  {new Date(team.founded_at).getFullYear()}年
                </dd>
              </div>
            )}
            {team.country && (
              <div>
                <dt className="text-slate-500">国</dt>
                <dd className="mt-0.5 font-semibold text-white">{team.country}</dd>
              </div>
            )}
            {team.region && (
              <div>
                <dt className="text-slate-500">リージョン</dt>
                <dd className="mt-0.5 font-semibold text-white">{team.region}</dd>
              </div>
            )}
          </dl>
        </section>
      )}
    </div>
  );
}

function DetailCard({
  icon: Icon,
  iconColor,
  iconBg,
  label,
  main,
  sub,
}: {
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  label: string;
  main: string;
  sub: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-4">
      <div className={cn("mb-3 inline-flex rounded-lg p-2", iconBg)}>
        <Icon className={cn("h-4 w-4", iconColor)} />
      </div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-xl font-black text-white">{main}</p>
      <p className="mt-0.5 text-xs text-slate-500">{sub}</p>
    </div>
  );
}

function WinLossBar({
  label,
  wins,
  losses,
  winColor,
}: {
  label: string;
  wins: number;
  losses: number;
  winColor: string;
}) {
  const total = wins + losses;
  const winPct = total > 0 ? (wins / total) * 100 : 0;
  const lossPct = 100 - winPct;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-slate-400">{label}</span>
        <div className="flex items-center gap-3 text-slate-500">
          <span className="text-green-400 font-semibold">{wins}W</span>
          <span className="text-red-400 font-semibold">{losses}L</span>
          <span>{winPct.toFixed(1)}%</span>
        </div>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-red-500/30">
        <div
          className={cn("h-full rounded-full transition-all", winColor)}
          style={{ width: `${winPct}%` }}
        />
      </div>
    </div>
  );
}
