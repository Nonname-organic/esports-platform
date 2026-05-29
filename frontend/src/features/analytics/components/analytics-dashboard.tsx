"use client";

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import { cn } from "@/lib/utils";
import type { MapStats, CompositionStats, RankingEntry } from "@/types/analytics";

const CHART_COLORS = ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#06b6d4"];

// ===== マップ勝率チャート =====
interface MapWinRateChartProps {
  data: MapStats[];
}

export function MapWinRateChart({ data }: MapWinRateChartProps) {
  const chartData = data.map((m) => ({
    name: m.map_name || m.map_id.slice(0, 8),
    attack: Math.round(m.attack_win_rate * 100),
    defense: Math.round((1 - m.attack_win_rate) * 100),
    games: m.total_games,
  }));

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <div className="mb-4">
        <h3 className="font-bold text-white">マップ別 攻撃/守備 勝率</h3>
        <p className="text-xs text-slate-500 mt-0.5">全試合集計</p>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #ffffff20", borderRadius: 8 }}
            labelStyle={{ color: "#fff", fontWeight: "bold" }}
            itemStyle={{ color: "#94a3b8" }}
            formatter={(val: number, name: string) => [
              `${val}%`,
              name === "attack" ? "攻撃側" : "守備側",
            ]}
          />
          <Bar dataKey="attack" fill="#ef4444" name="attack" radius={[4, 4, 0, 0]} />
          <Bar dataKey="defense" fill="#3b82f6" name="defense" radius={[4, 4, 0, 0]} />
          <Legend
            formatter={(value) => (value === "attack" ? "攻撃側" : "守備側")}
            wrapperStyle={{ color: "#94a3b8", fontSize: 12 }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ===== 構成勝率テーブル =====
interface CompositionTableProps {
  data: CompositionStats[];
}

export function CompositionTable({ data }: CompositionTableProps) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <div className="mb-4">
        <h3 className="font-bold text-white">エージェント構成 勝率ランキング</h3>
        <p className="text-xs text-slate-500 mt-0.5">3試合以上のデータ</p>
      </div>
      <div className="space-y-2 max-h-80 overflow-y-auto scrollbar-thin">
        {data.map((comp, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2.5 hover:bg-white/10 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="w-5 text-center text-xs font-bold text-slate-500">#{i + 1}</span>
              <div className="flex flex-wrap gap-1">
                {comp.composition.map((agent) => (
                  <span
                    key={agent}
                    className="rounded bg-brand-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-brand-400"
                  >
                    {agent}
                  </span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold text-white text-sm">
                {Math.round(comp.win_rate * 100)}%
              </p>
              <p className="text-[10px] text-slate-500">{comp.games_played}試合</p>
            </div>
          </div>
        ))}
        {data.length === 0 && (
          <p className="text-center text-sm text-slate-500 py-8">データなし</p>
        )}
      </div>
    </div>
  );
}

// ===== ランキングテーブル =====
interface RankingTableProps {
  data: RankingEntry[];
  title?: string;
}

export function RankingTable({ data, title = "ランキング" }: RankingTableProps) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 overflow-hidden">
      <div className="border-b border-white/10 px-5 py-4">
        <h3 className="font-bold text-white">{title}</h3>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/5 text-xs text-slate-500">
            <th className="px-4 py-3 text-left">#</th>
            <th className="px-4 py-3 text-left">チーム</th>
            <th className="px-4 py-3 text-center">勝利</th>
            <th className="px-4 py-3 text-center">敗北</th>
            <th className="px-4 py-3 text-center">勝率</th>
            <th className="px-4 py-3 text-right">Pt</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {data.map((entry) => (
            <tr
              key={entry.team_id}
              className={cn(
                "hover:bg-white/5 transition-colors",
                entry.rank_position <= 3 && "bg-yellow-500/5",
              )}
            >
              <td className="px-4 py-3">
                <RankBadge position={entry.rank_position} />
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2.5">
                  {entry.team_logo_url ? (
                    <img src={entry.team_logo_url} alt="" className="h-7 w-7 object-contain" />
                  ) : (
                    <div className="h-7 w-7 rounded bg-white/10 flex items-center justify-center">
                      <span className="text-[10px] font-bold text-slate-400">
                        {entry.team_tag.slice(0, 2)}
                      </span>
                    </div>
                  )}
                  <div>
                    <p className="font-semibold text-sm text-white">{entry.team_name}</p>
                    <p className="text-xs text-slate-500">{entry.team_tag}</p>
                  </div>
                </div>
              </td>
              <td className="px-4 py-3 text-center text-sm text-green-400 font-mono">
                {entry.wins}
              </td>
              <td className="px-4 py-3 text-center text-sm text-red-400 font-mono">
                {entry.losses}
              </td>
              <td className="px-4 py-3 text-center">
                <WinRateBar rate={entry.win_rate} />
              </td>
              <td className="px-4 py-3 text-right font-bold text-white">
                {entry.points}
              </td>
            </tr>
          ))}
          {data.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">
                ランキングデータがありません
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function RankBadge({ position }: { position: number }) {
  if (position === 1) return <span className="text-base">🥇</span>;
  if (position === 2) return <span className="text-base">🥈</span>;
  if (position === 3) return <span className="text-base">🥉</span>;
  return <span className="text-sm font-bold text-slate-400">{position}</span>;
}

function WinRateBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/10">
        <div
          className={cn(
            "h-full rounded-full",
            pct >= 60 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-400 w-10 text-right">{pct}%</span>
    </div>
  );
}

// ===== 選手KDAレーダーチャート =====
interface PlayerRadarProps {
  players: Array<{
    name: string;
    kda: number;
    kills: number;
    assists: number;
    firstBloods: number;
    winRate: number;
  }>;
}

export function PlayerRadarChart({ players }: PlayerRadarProps) {
  if (players.length === 0) return null;

  const data = [
    { subject: "KDA", ...Object.fromEntries(players.map((p) => [p.name, Math.min(p.kda, 5)])) },
    { subject: "Kills", ...Object.fromEntries(players.map((p) => [p.name, p.kills / 20])) },
    { subject: "Assists", ...Object.fromEntries(players.map((p) => [p.name, p.assists / 20])) },
    { subject: "FB", ...Object.fromEntries(players.map((p) => [p.name, p.firstBloods / 5])) },
    { subject: "Win率", ...Object.fromEntries(players.map((p) => [p.name, p.winRate * 5])) },
  ];

  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-5">
      <h3 className="mb-4 font-bold text-white">選手パフォーマンス比較</h3>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data}>
          <PolarGrid stroke="#ffffff15" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          {players.map((p, i) => (
            <Radar
              key={p.name}
              name={p.name}
              dataKey={p.name}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              fill={CHART_COLORS[i % CHART_COLORS.length]}
              fillOpacity={0.15}
            />
          ))}
          <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #ffffff20", borderRadius: 8 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
