"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Calendar, Radio, X, ExternalLink } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import type { BracketMatch, BracketResponse, BracketSide } from "@/types/tournament";

// ── レイアウト定数 ─────────────────────────────────────────────────────────────
const CARD_W = 220;
const CARD_H = 80;
const SLOT_H = CARD_H + 12;
const COL_GAP = 48;        // ラウンド間の水平ギャップ
const COL_W = CARD_W + COL_GAP;

const MIN_ZOOM = 0.4;
const MAX_ZOOM = 2.0;
const ZOOM_STEP = 0.15;

// ── 型 ────────────────────────────────────────────────────────────────────────
interface PositionedMatch {
  match: BracketMatch;
  x: number;
  y: number;
  centerY: number;
}

interface RoundData {
  roundNum: number;
  label: string;
  matches: PositionedMatch[];
}

interface BracketViewProps {
  bracket: BracketResponse;
  className?: string;
}

// ── ユーティリティ ────────────────────────────────────────────────────────────

function getRoundLabel(fromEnd: number, format: string, side?: BracketSide | null): string {
  if (format === "round_robin") return `第${fromEnd}ラウンド`;
  if (side === "losers") {
    if (fromEnd === 1) return "敗者決勝";
    return `敗者 R${fromEnd}`;
  }
  if (side === "grand_finals") return "グランドファイナル";
  if (fromEnd === 1) return "決勝";
  if (fromEnd === 2) return "準決勝";
  if (fromEnd === 3) return "準々決勝";
  return `Round ${fromEnd}`;
}

function buildLayout(rounds: { roundNum: number; matches: BracketMatch[] }[]): {
  layoutRounds: RoundData[];
  totalWidth: number;
  totalHeight: number;
} {
  const firstRoundCount = rounds[0]?.matches.length ?? 1;
  const totalHeight = firstRoundCount * SLOT_H + CARD_H;
  const layoutRounds: RoundData[] = [];

  rounds.forEach(({ roundNum, matches }, ri) => {
    const slotsPerMatch = Math.pow(2, ri);
    const posMatches: PositionedMatch[] = matches.map((match, mi) => {
      const y = mi * slotsPerMatch * SLOT_H + ((slotsPerMatch * SLOT_H - CARD_H) / 2);
      const centerY = y + CARD_H / 2;
      return { match, x: ri * COL_W, y, centerY };
    });

    const side = matches[0]?.bracket_side ?? null;
    const fromEnd = rounds.length - ri;
    layoutRounds.push({
      roundNum,
      label: getRoundLabel(fromEnd, "single_elimination", side),
      matches: posMatches,
    });
  });

  const totalWidth = rounds.length * COL_W;
  return { layoutRounds, totalWidth, totalHeight };
}

function buildDELayout(allRounds: { roundNum: number; matches: BracketMatch[] }[]): {
  winners: RoundData[];
  losers: RoundData[];
  finals: RoundData[];
  totalWidth: number;
  totalHeight: number;
} {
  const winnerRounds = allRounds.filter(r =>
    r.matches.some(m => m.bracket_side === "winners" || m.bracket_side == null)
    && !r.matches.some(m => m.bracket_side === "grand_finals" || m.bracket_side === "losers")
  );
  const loserRounds = allRounds.filter(r =>
    r.matches.some(m => m.bracket_side === "losers")
  );
  const finalRounds = allRounds.filter(r =>
    r.matches.some(m => m.bracket_side === "grand_finals")
  );

  // fallback: split by round count for SE-like API
  if (winnerRounds.length === 0 && loserRounds.length === 0) {
    const half = Math.ceil(allRounds.length / 2);
    const se = allRounds.slice(0, half);
    const { layoutRounds: w, totalHeight: wH } = buildLayout(se);
    return {
      winners: w,
      losers: [],
      finals: [],
      totalWidth: allRounds.length * COL_W,
      totalHeight: wH,
    };
  }

  const { layoutRounds: wRounds, totalHeight: wH } = buildLayout(
    winnerRounds.map(r => ({ roundNum: r.roundNum, matches: r.matches }))
  );
  const { layoutRounds: lRounds, totalHeight: lH } = buildLayout(
    loserRounds.map(r => ({ roundNum: r.roundNum, matches: r.matches }))
  );
  const finalsLayouts: RoundData[] = finalRounds.map((r, ri) => ({
    roundNum: r.roundNum,
    label: "グランドファイナル",
    matches: r.matches.map((match, mi) => ({
      match,
      x: (winnerRounds.length + ri) * COL_W,
      y: mi * (CARD_H + 12),
      centerY: mi * (CARD_H + 12) + CARD_H / 2,
    })),
  }));

  return {
    winners: wRounds,
    losers: lRounds,
    finals: finalsLayouts,
    totalWidth: (winnerRounds.length + loserRounds.length + finalRounds.length) * COL_W,
    totalHeight: wH + lH + 48,
  };
}

// ── メインコンポーネント ───────────────────────────────────────────────────────
export function BracketView({ bracket, className }: BracketViewProps) {
  const [zoom, setZoom] = useState(1);
  const [selected, setSelected] = useState<BracketMatch | null>(null);
  const outerRef = useRef<HTMLDivElement>(null);

  const changeZoom = useCallback((delta: number) => {
    setZoom(z => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z + delta)));
  }, []);

  // Ctrl + scroll でズーム
  useEffect(() => {
    const el = outerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        changeZoom(-e.deltaY * 0.003);
      }
    };
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, [changeZoom]);

  const sortedRounds = Object.entries(bracket.rounds)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([rn, matches]) => ({
      roundNum: Number(rn),
      matches: [...matches].sort((a, b) => a.match_number - b.match_number),
    }));

  const isDE = bracket.format === "double_elimination";

  const { layoutRounds, winners, losers, finals, totalWidth, totalHeight } = (() => {
    if (isDE) {
      const de = buildDELayout(sortedRounds);
      return { layoutRounds: [], ...de };
    }
    const se = buildLayout(sortedRounds);
    return { ...se, winners: [], losers: [], finals: [] };
  })();

  const rounds = isDE ? [...winners, ...finals] : layoutRounds;

  return (
    <div className={cn("relative flex flex-col", className)}>
      {/* ── ズームコントロール ── */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {bracket.format === "double_elimination" ? "ダブルエリミネーション" : "シングルエリミネーション"}
          </span>
          <span className="text-xs text-slate-600">•</span>
          <span className="text-xs text-slate-500">Ctrl+スクロールでズーム</span>
        </div>
        <ZoomControls
          zoom={zoom}
          onZoomIn={() => changeZoom(ZOOM_STEP)}
          onZoomOut={() => changeZoom(-ZOOM_STEP)}
          onReset={() => setZoom(1)}
        />
      </div>

      {/* ── キャンバス ── */}
      <div
        ref={outerRef}
        className="overflow-auto rounded-xl border border-white/10 bg-slate-950"
        style={{ cursor: "grab" }}
      >
        <div
          className="relative p-8 transition-transform duration-100"
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: "top left",
            width: totalWidth + 64,
            height: (isDE ? totalHeight + 80 : totalHeight) + 64,
            minWidth: "max-content",
          }}
        >
          {/* Winners / SE ブラケット */}
          <BracketGrid
            rounds={rounds}
            totalRounds={rounds.length}
            onSelect={setSelected}
            selected={selected}
          />

          {/* Losers ブラケット（DE） */}
          {isDE && losers.length > 0 && (
            <div style={{ marginTop: 48 }}>
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-600">
                Losers Bracket
              </p>
              <BracketGrid
                rounds={losers}
                totalRounds={losers.length}
                onSelect={setSelected}
                selected={selected}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── マッチ詳細パネル ── */}
      {selected && (
        <MatchDetailPanel match={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

// ── ブラケットグリッド（SE / Winnersブラケット共用）──────────────────────────
interface BracketGridProps {
  rounds: RoundData[];
  totalRounds: number;
  onSelect: (m: BracketMatch) => void;
  selected: BracketMatch | null;
}

function BracketGrid({ rounds, totalRounds, onSelect, selected }: BracketGridProps) {
  if (rounds.length === 0) return null;
  const firstRoundCount = rounds[0]?.matches.length ?? 1;
  const gridH = firstRoundCount * SLOT_H + CARD_H;

  return (
    <div className="relative" style={{ height: gridH, width: totalRounds * COL_W }}>
      {/* SVGコネクター */}
      <svg
        className="pointer-events-none absolute inset-0"
        width={totalRounds * COL_W}
        height={gridH}
      >
        {rounds.slice(0, -1).map(({ matches }, ri) => (
          <g key={ri}>
            {matches.map(({ match, centerY }, mi) => {
              // 対応する次ラウンドのマッチ
              const nextRound = rounds[ri + 1];
              if (!nextRound) return null;
              const parentMatch = nextRound.matches[Math.floor(mi / 2)];
              if (!parentMatch) return null;

              const x1 = ri * COL_W + CARD_W;
              const x2 = (ri + 1) * COL_W;
              const xMid = x1 + COL_GAP / 2;

              return (
                <g key={match.id}>
                  {/* マッチ右端 → 垂直線の合流点 */}
                  <line
                    x1={x1} y1={centerY}
                    x2={xMid} y2={centerY}
                    stroke="rgba(255,255,255,0.12)"
                    strokeWidth="1.5"
                  />
                  {/* 合流点 → 次マッチ左端 (偶数・奇数ペアの最後だけ描画) */}
                  {mi % 2 === 1 && (
                    <>
                      <line
                        x1={xMid} y1={rounds[ri].matches[mi - 1].centerY}
                        x2={xMid} y2={centerY}
                        stroke="rgba(255,255,255,0.12)"
                        strokeWidth="1.5"
                      />
                      <line
                        x1={xMid} y1={parentMatch.centerY}
                        x2={x2} y2={parentMatch.centerY}
                        stroke="rgba(255,255,255,0.12)"
                        strokeWidth="1.5"
                      />
                    </>
                  )}
                </g>
              );
            })}
          </g>
        ))}
      </svg>

      {/* ラウンドヘッダー + カード */}
      {rounds.map(({ roundNum, label, matches }, ri) => (
        <div
          key={roundNum}
          className="absolute top-0"
          style={{ left: ri * COL_W, width: CARD_W }}
        >
          {/* ラウンドラベル */}
          <div className="mb-3 flex items-center justify-center">
            <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-500">
              {label}
            </span>
          </div>

          {/* マッチカード群 */}
          {matches.map(({ match, y }) => (
            <div
              key={match.id}
              className="absolute"
              style={{ top: y + 28, width: CARD_W }}
            >
              <BracketMatchCard
                match={match}
                isSelected={selected?.id === match.id}
                onClick={() => onSelect(match)}
              />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── マッチカード ──────────────────────────────────────────────────────────────
interface BracketMatchCardProps {
  match: BracketMatch;
  isSelected: boolean;
  onClick: () => void;
}

function BracketMatchCard({ match, isSelected, onClick }: BracketMatchCardProps) {
  const isOngoing = match.status === "ongoing";
  const isCompleted = match.status === "completed";

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full overflow-hidden rounded-lg border bg-slate-900 text-left transition-all duration-150",
        "hover:border-brand-500/50 hover:shadow-md hover:shadow-brand-500/10",
        "focus:outline-none focus:ring-2 focus:ring-brand-500/50",
        isSelected && "border-brand-500/70 shadow-md shadow-brand-500/10",
        isOngoing && !isSelected && "border-red-500/40 shadow-sm shadow-red-500/10",
        !isOngoing && !isSelected && "border-white/8",
      )}
      aria-label={`${match.team1?.name ?? "TBD"} vs ${match.team2?.name ?? "TBD"}`}
    >
      {/* ステータスバー */}
      {isOngoing && (
        <div className="flex items-center gap-1.5 border-b border-red-500/20 bg-red-500/10 px-2.5 py-1">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-red-400">Live</span>
        </div>
      )}
      {!isOngoing && (
        <div className="border-b border-white/5 px-2.5 py-1">
          <span className="text-[10px] text-slate-600">
            M{match.match_number}
            {match.scheduled_at && (
              <span className="ml-1.5">· {new Date(match.scheduled_at).toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" })}</span>
            )}
          </span>
        </div>
      )}

      {/* Team 1 */}
      <TeamRow
        team={match.team1}
        seed={match.team1_seed}
        isWinner={isCompleted && match.winner_id === match.team1?.id}
        isLoser={isCompleted && !!match.winner_id && match.winner_id !== match.team1?.id}
      />

      <div className="border-t border-white/5" />

      {/* Team 2 */}
      <TeamRow
        team={match.team2}
        seed={match.team2_seed}
        isWinner={isCompleted && match.winner_id === match.team2?.id}
        isLoser={isCompleted && !!match.winner_id && match.winner_id !== match.team2?.id}
      />
    </button>
  );
}

interface TeamRowProps {
  team: BracketMatch["team1"];
  seed: number | null | undefined;
  isWinner: boolean;
  isLoser: boolean;
}

function TeamRow({ team, seed, isWinner, isLoser }: TeamRowProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-2.5 py-2 transition-colors",
        isWinner && "bg-brand-500/8",
        isLoser && "opacity-35",
        !team && "opacity-25",
      )}
    >
      {/* シード番号 */}
      {seed != null && (
        <span className="flex-shrink-0 text-[10px] font-bold text-slate-600 w-3 text-center">
          {seed}
        </span>
      )}

      {/* ロゴ */}
      <div className="h-6 w-6 flex-shrink-0 overflow-hidden rounded">
        {team?.logo_url ? (
          <img src={team.logo_url} alt={team.name ?? ""} className="h-full w-full object-contain" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-white/8">
            <span className="text-[9px] font-bold text-slate-500">
              {team?.tag?.slice(0, 2) ?? "?"}
            </span>
          </div>
        )}
      </div>

      {/* チーム名 */}
      <div className="flex-1 min-w-0">
        {team ? (
          <p className={cn("truncate text-xs font-semibold leading-tight", isWinner ? "text-brand-400" : "text-slate-200")}>
            {team.name}
          </p>
        ) : (
          <p className="text-xs text-slate-600">TBD</p>
        )}
      </div>

      {/* 勝者マーク */}
      {isWinner && (
        <svg className="h-3.5 w-3.5 flex-shrink-0 text-brand-400" fill="currentColor" viewBox="0 0 16 16">
          <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
        </svg>
      )}
    </div>
  );
}

// ── ズームコントロール ─────────────────────────────────────────────────────────
interface ZoomControlsProps {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

function ZoomControls({ zoom, onZoomIn, onZoomOut, onReset }: ZoomControlsProps) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-slate-900 px-1 py-1">
      <button
        onClick={onZoomOut}
        disabled={zoom <= MIN_ZOOM}
        className="rounded p-1.5 text-slate-400 hover:bg-white/5 hover:text-white disabled:opacity-30 transition-colors"
        aria-label="ズームアウト"
      >
        <ZoomOut className="h-3.5 w-3.5" />
      </button>

      <button
        onClick={onReset}
        className="min-w-[3rem] rounded px-2 py-1 text-xs font-mono text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
        aria-label="ズームリセット"
      >
        {Math.round(zoom * 100)}%
      </button>

      <button
        onClick={onZoomIn}
        disabled={zoom >= MAX_ZOOM}
        className="rounded p-1.5 text-slate-400 hover:bg-white/5 hover:text-white disabled:opacity-30 transition-colors"
        aria-label="ズームイン"
      >
        <ZoomIn className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ── マッチ詳細パネル ──────────────────────────────────────────────────────────
interface MatchDetailPanelProps {
  match: BracketMatch;
  onClose: () => void;
}

function MatchDetailPanel({ match, onClose }: MatchDetailPanelProps) {
  const isCompleted = match.status === "completed";
  const isOngoing = match.status === "ongoing";

  const STATUS_LABEL: Record<string, string> = {
    scheduled: "予定",
    ongoing: "進行中",
    completed: "終了",
    cancelled: "中止",
    forfeit: "没収試合",
    no_show: "不戦敗",
  };

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-white/10 bg-slate-900 shadow-xl">
      {/* ヘッダー */}
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <div className="flex items-center gap-2">
          {isOngoing && <Radio className="h-4 w-4 animate-pulse text-red-400" />}
          <span className="text-sm font-semibold text-white">
            Round {match.round_number} - Match {match.match_number}
          </span>
          <span className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            isOngoing ? "bg-red-500/10 text-red-400" :
            isCompleted ? "bg-slate-500/10 text-slate-400" :
            "bg-white/5 text-slate-500"
          )}>
            {STATUS_LABEL[match.status] ?? match.status}
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-slate-500 hover:bg-white/5 hover:text-white transition-colors"
          aria-label="閉じる"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* チーム対戦 */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 px-6 py-5">
        {/* Team 1 */}
        <TeamDetail
          team={match.team1}
          seed={match.team1_seed}
          isWinner={isCompleted && match.winner_id === match.team1?.id}
          align="left"
        />

        {/* VS */}
        <div className="text-center">
          <p className="text-xl font-black text-slate-600">VS</p>
        </div>

        {/* Team 2 */}
        <TeamDetail
          team={match.team2}
          seed={match.team2_seed}
          isWinner={isCompleted && match.winner_id === match.team2?.id}
          align="right"
        />
      </div>

      {/* メタ情報 */}
      <div className="border-t border-white/10 px-5 py-3 space-y-1.5">
        {match.scheduled_at && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Calendar className="h-3.5 w-3.5" />
            <span>{formatDate(match.scheduled_at)}</span>
          </div>
        )}
        {match.bracket_side && (
          <p className="text-xs text-slate-600">
            {match.bracket_side === "winners" ? "Winners Bracket" :
             match.bracket_side === "losers" ? "Losers Bracket" : "Grand Finals"}
          </p>
        )}
      </div>
    </div>
  );
}

interface TeamDetailProps {
  team: BracketMatch["team1"];
  seed: number | null | undefined;
  isWinner: boolean;
  align: "left" | "right";
}

function TeamDetail({ team, seed, isWinner, align }: TeamDetailProps) {
  return (
    <div className={cn("flex flex-col items-center gap-2", align === "right" && "")}>
      {/* ロゴ */}
      <div className={cn(
        "h-14 w-14 overflow-hidden rounded-xl border",
        isWinner ? "border-brand-500/40" : "border-white/10"
      )}>
        {team?.logo_url ? (
          <img src={team.logo_url} alt={team.name ?? ""} className="h-full w-full object-contain" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-white/5">
            <span className="text-sm font-bold text-slate-500">{team?.tag?.slice(0, 3) ?? "TBD"}</span>
          </div>
        )}
      </div>

      {/* チーム名 */}
      <div className={cn("text-center", !team && "opacity-40")}>
        {seed != null && (
          <span className="mb-0.5 block text-[10px] font-semibold text-slate-600">
            #{seed} シード
          </span>
        )}
        <p className={cn("text-sm font-bold", isWinner ? "text-brand-400" : "text-white")}>
          {team?.name ?? "TBD"}
        </p>
        {team?.tag && <p className="text-xs text-slate-500">{team.tag}</p>}
        {isWinner && (
          <span className="mt-1 inline-block rounded-full bg-brand-500/10 px-2 py-0.5 text-xs font-semibold text-brand-400">
            WINNER
          </span>
        )}
      </div>
    </div>
  );
}
