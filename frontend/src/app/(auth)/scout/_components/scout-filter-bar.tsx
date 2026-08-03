"use client";

import { Filter } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * LFT / LFP 共通の絞り込みバー。
 * ステータスは色付きピル（ワンクリック切替・現在値が一目で分かる）、
 * ロール/ランク/地域はラベル付きセレクトを3カラムグリッドで幅いっぱいに配置し、
 * 左寄せの空きスペースをなくす。
 */
export interface ScoutStatusOption {
  value: string; // "" = すべて
  label: string;
  dot?: string; // ドットの色クラス（すべて には不要）
  activeCls: string; // 選択時のピル配色
}

export function ScoutFilterBar({
  statusOptions,
  status,
  onStatus,
  role,
  onRole,
  roles,
  rankMin,
  onRankMin,
  rankMax,
  onRankMax,
  ranks,
  region,
  onRegion,
  regions,
}: {
  statusOptions: ScoutStatusOption[];
  status: string;
  onStatus: (v: string) => void;
  role: string;
  onRole: (v: string) => void;
  roles: readonly string[];
  rankMin: string;
  onRankMin: (v: string) => void;
  rankMax: string;
  onRankMax: (v: string) => void;
  ranks: readonly string[];
  region: string;
  onRegion: (v: string) => void;
  regions: readonly string[];
}) {
  const sel =
    "w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-brand-500";

  return (
    <div className="mb-6 space-y-3 rounded-2xl border border-white/10 bg-slate-900 p-4">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
        <Filter className="h-3.5 w-3.5" />
        絞り込み
      </div>

      {/* ステータス: 色付きピル */}
      <div className="flex flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
        <span className="hidden select-none px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500 sm:inline">
          ステータス
        </span>
        {statusOptions.map(({ value, label, dot, activeCls }) => (
          <button
            key={value || "ALL"}
            onClick={() => onStatus(value)}
            aria-pressed={status === value}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg border border-transparent px-3 py-1.5 text-sm font-medium transition-colors",
              status === value ? activeCls : "text-slate-400 hover:text-white",
            )}
          >
            {dot && <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />}
            {label}
          </button>
        ))}
      </div>

      {/* 条件セレクト: 幅いっぱいの4カラム（ランクは最低〜最高の範囲指定） */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            ロール
          </span>
          <select value={role} onChange={(e) => onRole(e.target.value)} className={sel}>
            <option value="">すべて</option>
            {roles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            最低ランク
          </span>
          <select value={rankMin} onChange={(e) => onRankMin(e.target.value)} className={sel}>
            <option value="">指定なし</option>
            {ranks.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            最高ランク
          </span>
          <select value={rankMax} onChange={(e) => onRankMax(e.target.value)} className={sel}>
            <option value="">指定なし</option>
            {ranks.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            地域
          </span>
          <select value={region} onChange={(e) => onRegion(e.target.value)} className={sel}>
            <option value="">すべて</option>
            {regions.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
