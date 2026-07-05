"use client";

import { Trophy, Crosshair, Target, Users, Twitter } from "lucide-react";
import Link from "next/link";
import { usePlayerCareer } from "@/features/career/hooks/use-career";
import type { Player } from "@/types/player";
import { SummaryCard } from "./shared/summary-card";
import { StatsGrid } from "./shared/stats-grid";
import { TabSkeleton } from "./shared/empty-state";
import { fmtNum, fmtInt, fmtPct, DASH } from "./shared/stat-format";
import { PlayerRankCard } from "./player-rank-card";
import { AiAnalysisCard } from "@/components/player-profile/ai-analysis-card";
import { CareerStatisticsCard } from "@/components/player-profile/career-statistics-card";
import { AgentPoolCard } from "@/components/player-profile/agent-pool-card";
import { MapPerformanceCard } from "@/components/player-profile/map-performance-card";
import { TournamentHistoryCard } from "@/components/player-profile/tournament-history-card";

interface Props {
  player: Player;
  playerId: string;
}

export function PlayerOverview({ player, playerId }: Props) {
  const { data: career, isLoading } = usePlayerCareer(playerId);

  if (isLoading) return <TabSkeleton rows={2} />;

  const kd = career && career.avg_deaths ? career.avg_kills / career.avg_deaths : null;

  return (
    <div className="space-y-6 pt-6">
      {/* 基本情報 */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
          <Users className="h-4 w-4 text-brand-400" /> 基本情報
        </h2>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm lg:grid-cols-3">
          <Info label="Player" value={player.display_name} />
          <Info label="ゲーム内名" value={player.in_game_name ?? DASH} />
          <Info label="所属チーム" value={player.team_name ?? "フリー"} href={player.team_id ? `/teams/${player.team_id}` : undefined} />
          <Info label="メインロール" value={player.role ?? DASH} />
        </div>
        {(player as any).twitter_handle && (
          <a href={`https://twitter.com/${(player as any).twitter_handle}`} target="_blank" rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1.5 text-xs text-sky-400 hover:underline">
            <Twitter className="h-3.5 w-3.5" /> @{(player as any).twitter_handle}
          </a>
        )}
        {player.bio && <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{player.bio}</p>}
      </section>

      {/* ランクカード（競技ランキング / ADR-0016） */}
      <PlayerRankCard playerId={playerId} />

      {/* AI 分析（ADR-0018 / Read Only・Provider化） */}
      <AiAnalysisCard playerId={playerId} />

      {/* Career / Agent / Map / History Widget（独立・ADR-0018） */}
      <CareerStatisticsCard playerId={playerId} />
      <AgentPoolCard playerId={playerId} />
      <MapPerformanceCard playerId={playerId} />
      <TournamentHistoryCard playerId={playerId} />

      {/* KPIサマリー */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard icon={Trophy} iconBg="bg-brand-500/10" iconColor="text-brand-400"
          label="大会勝率" main={fmtPct(career?.win_rate)} sub={`${fmtInt(career?.total_matches)} 試合`} />
        <SummaryCard icon={Crosshair} iconBg="bg-green-500/10" iconColor="text-green-400"
          label="KDA" main={fmtNum(career?.avg_kda, 2)} sub={`ACS ${fmtNum(career?.avg_acs, 0)}`} />
        <SummaryCard icon={Target} iconBg="bg-yellow-500/10" iconColor="text-yellow-400"
          label="優勝回数" main={fmtInt(career?.championships)} sub={`MVP ${fmtInt(career?.mvp_count)}`} />
        <SummaryCard icon={Trophy} iconBg="bg-purple-500/10" iconColor="text-purple-400"
          label="大会参加数" main={fmtInt(career?.tournaments_played)} sub={`${fmtInt(career?.total_wins)}W ${fmtInt(career?.total_losses)}L`} />
      </div>

      {/* 大会サマリー */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <Trophy className="h-4 w-4 text-brand-400" /> 大会サマリー
        </h2>
        <StatsGrid
          cols={4}
          items={[
            { label: "大会参加数", value: fmtInt(career?.tournaments_played), highlight: true },
            { label: "大会勝率", value: fmtPct(career?.win_rate) },
            { label: "大会総試合数", value: fmtInt(career?.total_matches) },
            { label: "優勝回数", value: fmtInt(career?.championships) },
            { label: "大会ACS", value: fmtNum(career?.avg_acs, 0) },
            { label: "大会KDA", value: fmtNum(career?.avg_kda, 2) },
            { label: "大会KD", value: fmtNum(kd, 2) },
            { label: "MVP回数", value: fmtInt(career?.mvp_count) },
          ]}
        />
      </div>

      {/* 詳細スタッツ */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <Crosshair className="h-4 w-4 text-brand-400" /> 詳細スタッツ
        </h2>
        <StatsGrid
          cols={3}
          items={[
            { label: "勝利", value: fmtInt(career?.total_wins) },
            { label: "敗北", value: fmtInt(career?.total_losses) },
            { label: "平均Kill", value: fmtNum(career?.avg_kills, 1) },
            { label: "平均Death", value: fmtNum(career?.avg_deaths, 1) },
            { label: "平均Assist", value: fmtNum(career?.avg_assists, 1) },
            { label: "最多使用Agent", value: career?.agent_usage?.[0]?.agent ?? DASH },
          ]}
        />
      </div>
    </div>
  );
}

function Info({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-500">{label}</span>
      {href ? (
        <Link href={href} className="mt-0.5 font-semibold text-brand-400 hover:underline">{value}</Link>
      ) : (
        <span className="mt-0.5 font-semibold text-white">{value}</span>
      )}
    </div>
  );
}
