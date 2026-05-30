import { Trophy, Crosshair, Target, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Player, PlayerCareerStats } from "@/types/player";

interface OverviewTabProps {
  player: Player;
  stats: PlayerCareerStats;
}

export function OverviewTab({ player, stats }: OverviewTabProps) {
  const winRatePct = (stats.win_rate * 100).toFixed(1);
  const hsRatePct = (stats.headshot_rate * 100).toFixed(1);
  const fbRatePct = (stats.first_blood_rate * 100).toFixed(1);

  return (
    <div className="space-y-6 pt-6">
      {/* サマリーカード */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard
          icon={Trophy}
          iconBg="bg-brand-500/10"
          iconColor="text-brand-400"
          label="勝敗"
          main={`${stats.wins}W / ${stats.losses}L`}
          sub={`${stats.total_matches} 試合`}
        />
        <SummaryCard
          icon={Crosshair}
          iconBg="bg-green-500/10"
          iconColor="text-green-400"
          label="KDA"
          main={stats.avg_kda.toFixed(2)}
          sub={`${stats.avg_kills.toFixed(1)} / ${stats.avg_deaths.toFixed(1)} / ${stats.avg_assists.toFixed(1)}`}
        />
        <SummaryCard
          icon={Target}
          iconBg="bg-red-500/10"
          iconColor="text-red-400"
          label="ヘッドショット率"
          main={`${hsRatePct}%`}
          sub="HS / Kill"
        />
        <SummaryCard
          icon={Zap}
          iconBg="bg-yellow-500/10"
          iconColor="text-yellow-400"
          label="ファーストブラッド"
          main={`${fbRatePct}%`}
          sub="FB / 試合"
        />
      </div>

      {/* レーティング */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-bold text-white">レーティング</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-slate-500">現在レーティング</p>
            <p className="mt-0.5 text-3xl font-black text-brand-400">
              {player.rating.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-slate-500">ピークレーティング</p>
            <p className="mt-0.5 text-3xl font-black text-yellow-400">
              {player.peak_rating.toLocaleString()}
            </p>
          </div>
        </div>
        <RatingBar current={player.rating} peak={player.peak_rating} />
      </section>

      {/* 詳細スタッツ */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-bold text-white">詳細スタッツ</h2>
        <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm lg:grid-cols-3">
          {[
            { label: "勝率", value: `${winRatePct}%` },
            { label: "平均スコア", value: stats.avg_score.toFixed(0) },
            { label: "平均Kill", value: stats.avg_kills.toFixed(1) },
            { label: "平均Death", value: stats.avg_deaths.toFixed(1) },
            { label: "平均Assist", value: stats.avg_assists.toFixed(1) },
            { label: "HS率", value: `${hsRatePct}%` },
            { label: "FB率", value: `${fbRatePct}%` },
            {
              label: "最多使用エージェント",
              value: stats.most_played_agent
                ? `${stats.most_played_agent} (${stats.most_played_agent_games}試合)`
                : "—",
            },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-slate-500">{label}</span>
              <span className="font-semibold text-white">{value}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Bio */}
      {player.bio && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-bold text-white">プロフィール</h2>
          <p className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">{player.bio}</p>
        </section>
      )}
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  iconBg,
  iconColor,
  label,
  main,
  sub,
}: {
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
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
      <p className="mt-0.5 text-lg font-black text-white">{main}</p>
      <p className="mt-0.5 text-xs text-slate-500">{sub}</p>
    </div>
  );
}

function RatingBar({ current, peak }: { current: number; peak: number }) {
  const pct = peak > 0 ? Math.min((current / peak) * 100, 100) : 0;
  return (
    <div className="mt-4">
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>0</span>
        <span>Peak: {peak.toLocaleString()}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-yellow-500/10">
        <div
          className="h-full rounded-full bg-brand-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
