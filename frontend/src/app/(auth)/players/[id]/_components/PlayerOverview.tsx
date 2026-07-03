"use client";

import { Trophy, Crosshair, Gamepad2, Target, Users, Link2, Twitter } from "lucide-react";
import Link from "next/link";
import { useCompetitive } from "@/features/riot/hooks/use-riot";
import { usePlayerCareer } from "@/features/career/hooks/use-career";
import type { Player } from "@/types/player";
import { SummaryCard } from "./shared/summary-card";
import { StatsGrid } from "./shared/stats-grid";
import { CompareCard, type CompareRow } from "./shared/compare-card";
import { TabSkeleton } from "./shared/empty-state";
import { fmtNum, fmtInt, fmtPct, DASH } from "./shared/stat-format";

interface Props {
  player: Player;
  playerId: string;
}

export function PlayerOverview({ player, playerId }: Props) {
  const { data: comp, isLoading: compLoading } = useCompetitive(playerId);
  const { data: career, isLoading: careerLoading } = usePlayerCareer(playerId);

  if (compLoading || careerLoading) return <TabSkeleton rows={2} />;

  const cs = comp?.summary;
  const cr = comp?.rank;

  // Quick Compare 行（Competitive vs Tournament）
  const compareRows: CompareRow[] = [
    {
      label: "勝率",
      competitive: fmtPct(cs?.win_rate),
      tournament: fmtPct(career?.win_rate),
      compBetter: cs && career ? cs.win_rate >= career.win_rate : null,
    },
    {
      label: "ACS",
      competitive: fmtNum(cs?.acs, 0),
      tournament: fmtNum(career?.avg_acs, 0),
      compBetter: cs && career ? cs.acs >= career.avg_acs : null,
    },
    { label: "ADR", competitive: fmtNum(cs?.adr, 0), tournament: DASH, compBetter: null },
    {
      label: "KDA",
      competitive: fmtNum(cs?.kda, 2),
      tournament: fmtNum(career?.avg_kda, 2),
      compBetter: cs && career ? cs.kda >= career.avg_kda : null,
    },
    {
      label: "KD",
      competitive: fmtNum(cs?.kd, 2),
      tournament: career ? fmtNum(career.avg_deaths ? career.avg_kills / career.avg_deaths : null, 2) : DASH,
      compBetter: null,
    },
    { label: "HS%", competitive: cs?.hs_rate != null ? fmtPct(cs.hs_rate) : DASH, tournament: DASH, compBetter: null },
  ];

  return (
    <div className="space-y-6 pt-6">
      {/* 基本情報 */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
          <Users className="h-4 w-4 text-brand-400" /> 基本情報
        </h2>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm lg:grid-cols-3">
          <Info label="Player" value={player.display_name} />
          <Info label="Riot ID" value={comp?.riot_id ?? player.in_game_name ?? DASH} />
          <Info label="所属チーム" value={player.team_name ?? "フリー"} href={player.team_id ? `/teams/${player.team_id}` : undefined} />
          <Info label="メインロール" value={player.role ?? DASH} />
          <Info label="現在ランク" value={cr?.current_rank ?? DASH} />
          <Info label="最高ランク" value={cr?.peak_rank ?? DASH} />
        </div>
        {(player as any).twitter_handle && (
          <a href={`https://twitter.com/${(player as any).twitter_handle}`} target="_blank" rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1.5 text-xs text-sky-400 hover:underline">
            <Twitter className="h-3.5 w-3.5" /> @{(player as any).twitter_handle}
          </a>
        )}
        {player.bio && <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{player.bio}</p>}
      </section>

      {/* KPIサマリー */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard icon={Gamepad2} iconBg="bg-red-500/10" iconColor="text-red-400"
          label="Competitive 勝率" main={fmtPct(cs?.win_rate)} sub={`${fmtInt(cs?.matches)} 試合`} />
        <SummaryCard icon={Trophy} iconBg="bg-brand-500/10" iconColor="text-brand-400"
          label="Tournament 勝率" main={fmtPct(career?.win_rate)} sub={`${fmtInt(career?.total_matches)} 試合`} />
        <SummaryCard icon={Crosshair} iconBg="bg-green-500/10" iconColor="text-green-400"
          label="Comp ACS" main={fmtNum(cs?.acs, 0)} sub={`KDA ${fmtNum(cs?.kda, 2)}`} />
        <SummaryCard icon={Target} iconBg="bg-yellow-500/10" iconColor="text-yellow-400"
          label="優勝回数" main={fmtInt(career?.championships)} sub={`MVP ${fmtInt(career?.mvp_count)}`} />
      </div>

      {/* Quick Compare */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <span className="rounded-md bg-gradient-to-r from-red-500/20 to-brand-500/20 px-2 py-0.5 text-xs">Quick Compare</span>
          Competitive vs Tournament
        </h2>
        <CompareCard rows={compareRows} />
      </div>

      {/* Riot Summary */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <Gamepad2 className="h-4 w-4 text-red-400" /> Riot Summary (Competitive)
        </h2>
        {comp?.linked ? (
          <StatsGrid
            cols={4}
            items={[
              { label: "現在ランク", value: cr?.current_rank ?? DASH, highlight: true },
              { label: "最高ランク", value: cr?.peak_rank ?? DASH },
              { label: "現在RR", value: fmtInt(cr?.current_rr) },
              { label: "総試合数", value: fmtInt(cs?.matches) },
              { label: "勝率", value: fmtPct(cs?.win_rate) },
              { label: "KD", value: fmtNum(cs?.kd, 2) },
              { label: "KDA", value: fmtNum(cs?.kda, 2) },
              { label: "ACS", value: fmtNum(cs?.acs, 0) },
              { label: "ADR", value: fmtNum(cs?.adr, 0) },
              { label: "HS%", value: cs?.hs_rate != null ? fmtPct(cs.hs_rate) : DASH },
              { label: "KAST", value: cs?.kast != null ? fmtPct(cs.kast) : DASH },
              { label: "MVP率", value: cs?.mvp_rate != null ? fmtPct(cs.mvp_rate) : DASH },
              { label: "直近20試合勝率", value: fmtPct(cs?.recent20_win_rate), highlight: true },
            ]}
          />
        ) : (
          <div className="flex items-center justify-between rounded-xl border border-dashed border-white/10 bg-slate-900 px-5 py-4">
            <p className="text-sm text-slate-400">Riot未連携です</p>
            <Link href={`/players/${playerId}?tab=competitive`} className="flex items-center gap-1.5 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/20 transition-colors">
              <Link2 className="h-3.5 w-3.5" /> Competitiveで連携
            </Link>
          </div>
        )}
      </div>

      {/* Tournament Summary */}
      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <Trophy className="h-4 w-4 text-brand-400" /> Tournament Summary
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
            { label: "大会KD", value: fmtNum(career && career.avg_deaths ? career.avg_kills / career.avg_deaths : null, 2) },
            { label: "MVP回数", value: fmtInt(career?.mvp_count) },
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
