"use client";

import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, ImageUp, Loader2, ScanLine, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ALL_VALORANT_AGENTS } from "@/lib/valorant";
import { matchApi } from "@/features/matches/api/match-api";
import { matchKeys } from "@/features/matches/hooks/use-matches";
import type {
  MatchDetail,
  ScoreboardParseResult,
  ScoreboardParseRow,
} from "@/types/match";

interface ScoreboardImportProps {
  match: MatchDetail;
}

/** 編集中の1行。OCR結果を初期値に、運営が修正できる状態で保持する */
interface EditableRow {
  key: string;
  ocrName: string;
  playerId: string;
  agent: string;
  acs: string;
  kills: string;
  deaths: string;
  assists: string;
  firstBloods: string;
  matchConfidence: number;
  /** 読み取れなかった項目（入力欄を強調する） */
  missing: string[];
}

/** 数値入力欄と、バックエンドが返す未読取ラベルの対応 */
const STAT_FIELDS: { field: keyof EditableRow & string; label: string }[] = [
  { field: "acs", label: "ACS" },
  { field: "kills", label: "K" },
  { field: "deaths", label: "D" },
  { field: "assists", label: "A" },
  { field: "firstBloods", label: "FB" },
];

function toEditable(row: ScoreboardParseRow, index: number): EditableRow {
  const num = (v: number | null) => (v == null ? "" : String(v));
  return {
    key: `${index}-${row.ocr_name}`,
    ocrName: row.ocr_name,
    playerId: row.player_id ?? "",
    agent: row.agent ?? "",
    acs: num(row.acs),
    kills: num(row.kills),
    deaths: num(row.deaths),
    assists: num(row.assists),
    firstBloods: num(row.first_bloods),
    matchConfidence: row.match_confidence,
    missing: row.missing ?? [],
  };
}

export function ScoreboardImport({ match }: ScoreboardImportProps) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [gameNumber, setGameNumber] = useState(1);
  const [parsed, setParsed] = useState<ScoreboardParseResult | null>(null);
  const [rows, setRows] = useState<EditableRow[]>([]);
  const [team1Score, setTeam1Score] = useState("");
  const [team2Score, setTeam2Score] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [dragging, setDragging] = useState(false);

  /** 選択された選手がどちらのチームかを候補一覧から引く */
  const teamIdOf = (playerId: string): string => {
    for (const team of parsed?.teams ?? []) {
      if (team.players.some((p) => p.id === playerId)) return team.id;
    }
    return "";
  };

  const parseMutation = useMutation({
    mutationFn: (file: File) => matchApi.parseScoreboard(match.id, file),
    onSuccess: (res) => {
      const data = res.data;
      setParsed(data);
      setRows(data.rows.map(toEditable));
      if (data.detected_score) {
        setTeam1Score(String(data.detected_score[0]));
        setTeam2Score(String(data.detected_score[1]));
      }
      setError(null);
      setSaved(false);
    },
    onError: (e: Error) => {
      setParsed(null);
      setRows([]);
      setError(e.message);
    },
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      matchApi.saveGamePlayerStats(match.id, gameNumber, {
        team1_score: Number(team1Score),
        team2_score: Number(team2Score),
        player_stats: rows
          .filter((r) => r.playerId)
          .map((r) => ({
            player_id: r.playerId,
            team_id: teamIdOf(r.playerId),
            agent: r.agent || null,
            kills: Number(r.kills) || 0,
            deaths: Number(r.deaths) || 0,
            assists: Number(r.assists) || 0,
            score: Number(r.acs) || 0,
            first_bloods: Number(r.firstBloods) || 0,
          })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matchKeys.detail(match.id) });
      setSaved(true);
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    setSaved(false);
    parseMutation.mutate(file);
  };

  const update = (key: string, field: keyof EditableRow, value: string) => {
    setRows((prev) =>
      prev.map((r) => (r.key === key ? { ...r, [field]: value } : r)),
    );
  };

  // 同じ選手を2行に割り当ててしまうと保存時に重複するため、事前に検出して止める
  const assigned = rows.map((r) => r.playerId).filter(Boolean);
  const duplicated = assigned.length !== new Set(assigned).size;
  const missingPlayer = rows.some((r) => !r.playerId);
  const scoreFilled = team1Score !== "" && team2Score !== "";
  const canSave =
    rows.length > 0 && !duplicated && !missingPlayer && scoreFilled &&
    !saveMutation.isPending;

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
        <ScanLine className="h-4 w-4 text-brand-400" />
        <h2 className="text-sm font-bold text-white">スコアボード取り込み</h2>
        <span className="ml-auto text-[11px] text-slate-500">
          スクリーンショット1枚で全選手の成績を登録
        </span>
      </div>

      <div className="space-y-4 p-5">
        {/* マップ選択 */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-400">マップ</label>
          <div className="flex gap-1.5">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setGameNumber(n)}
                className={cn(
                  "h-8 w-8 rounded-lg border text-xs font-bold transition-colors",
                  gameNumber === n
                    ? "border-brand-500/50 bg-brand-500/15 text-brand-300"
                    : "border-white/10 text-slate-500 hover:text-white",
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        {/* アップロード領域 */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFile(e.dataTransfer.files?.[0]);
          }}
          onClick={() => fileRef.current?.click()}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-8 text-center transition-colors",
            dragging
              ? "border-brand-500/60 bg-brand-500/5"
              : "border-white/15 hover:border-white/30",
          )}
        >
          {parseMutation.isPending ? (
            <>
              <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
              <p className="text-sm text-slate-400">スコアボードを解析中…</p>
            </>
          ) : (
            <>
              <ImageUp className="h-6 w-6 text-slate-500" />
              <p className="text-sm font-semibold text-white">
                スコアボードのスクリーンショットをドロップ
              </p>
              <p className="text-xs text-slate-500">
                クリックして選択も可能（PNG / JPEG / WebP）
              </p>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
        </div>

        {error && (
          <p className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            <X className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            {error}
          </p>
        )}

        {parsed && parsed.warnings.length > 0 && (
          <ul className="space-y-1.5 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2.5">
            {parsed.warnings.map((w) => (
              <li key={w} className="flex items-start gap-2 text-xs text-yellow-200">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
                {w}
              </li>
            ))}
          </ul>
        )}

        {parsed && (
          <>
            {/* ラウンドスコア */}
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-white/10 bg-slate-950/40 px-4 py-3">
              <span className="text-xs font-semibold text-slate-400">
                ラウンドスコア
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">
                  {match.team1?.name ?? "Team 1"}
                </span>
                <input
                  value={team1Score}
                  onChange={(e) => setTeam1Score(e.target.value.replace(/\D/g, ""))}
                  inputMode="numeric"
                  className="h-8 w-14 rounded-lg border border-white/10 bg-slate-900 px-2 text-center text-sm font-bold text-white"
                />
                <span className="text-slate-600">-</span>
                <input
                  value={team2Score}
                  onChange={(e) => setTeam2Score(e.target.value.replace(/\D/g, ""))}
                  inputMode="numeric"
                  className="h-8 w-14 rounded-lg border border-white/10 bg-slate-900 px-2 text-center text-sm font-bold text-white"
                />
                <span className="text-xs text-slate-400">
                  {match.team2?.name ?? "Team 2"}
                </span>
              </div>
            </div>

            {/* 編集テーブル */}
            <div className="overflow-x-auto rounded-lg border border-white/10">
              <table className="w-full min-w-max text-xs">
                <thead>
                  <tr className="border-b border-white/10 bg-slate-950/50 text-slate-500">
                    <th className="px-3 py-2.5 text-left font-medium">読み取り名</th>
                    <th className="px-3 py-2.5 text-left font-medium">選手</th>
                    <th className="px-3 py-2.5 text-left font-medium">エージェント</th>
                    <th className="px-2 py-2.5 text-center font-medium">ACS</th>
                    <th className="px-2 py-2.5 text-center font-medium">K</th>
                    <th className="px-2 py-2.5 text-center font-medium">D</th>
                    <th className="px-2 py-2.5 text-center font-medium">A</th>
                    <th className="px-2 py-2.5 text-center font-medium">FB</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {rows.map((row) => (
                    <tr key={row.key}>
                      <td className="px-3 py-2">
                        <span className="text-slate-400">{row.ocrName}</span>
                        {row.playerId && row.matchConfidence < 0.85 && (
                          <span
                            className="ml-1.5 text-yellow-400"
                            title="名前の一致度が低いため確認してください"
                          >
                            ?
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <select
                          value={row.playerId}
                          onChange={(e) => update(row.key, "playerId", e.target.value)}
                          className={cn(
                            "h-8 w-44 rounded-lg border bg-slate-900 px-2 text-xs text-white",
                            row.playerId ? "border-white/10" : "border-red-500/50",
                          )}
                        >
                          <option value="">選手を選択</option>
                          {(parsed.teams ?? []).map((team) => (
                            <optgroup key={team.id} label={team.name}>
                              {team.players.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.name}
                                </option>
                              ))}
                            </optgroup>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        <select
                          value={row.agent}
                          onChange={(e) => update(row.key, "agent", e.target.value)}
                          className={cn(
                            "h-8 w-32 rounded-lg border bg-slate-900 px-2 text-xs text-white",
                            row.agent ? "border-white/10" : "border-yellow-500/60",
                          )}
                        >
                          <option value="">未設定</option>
                          {ALL_VALORANT_AGENTS.map((a) => (
                            <option key={a} value={a}>
                              {a}
                            </option>
                          ))}
                        </select>
                      </td>
                      {STAT_FIELDS.map(({ field, label }) => (
                        <td key={field} className="px-2 py-2">
                          <input
                            value={row[field]}
                            onChange={(e) =>
                              update(row.key, field, e.target.value.replace(/\D/g, ""))
                            }
                            inputMode="numeric"
                            title={
                              row.missing.includes(label)
                                ? "読み取れませんでした。入力してください"
                                : undefined
                            }
                            className={cn(
                              "h-8 w-14 rounded-lg border bg-slate-900 px-2 text-center text-xs text-white",
                              row.missing.includes(label)
                                ? "border-yellow-500/60"
                                : "border-white/10",
                            )}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 保存 */}
            <div className="flex flex-wrap items-center justify-end gap-3">
              {duplicated && (
                <p className="text-xs text-red-400">
                  同じ選手が複数行に設定されています
                </p>
              )}
              {!duplicated && missingPlayer && (
                <p className="text-xs text-red-400">
                  選手が未選択の行があります
                </p>
              )}
              {!duplicated && !missingPlayer && !scoreFilled && (
                <p className="text-xs text-red-400">
                  ラウンドスコアを入力してください
                </p>
              )}
              {saved && (
                <p className="flex items-center gap-1.5 text-xs text-green-400">
                  <Check className="h-3.5 w-3.5" />
                  マップ{gameNumber}の成績を保存しました
                </p>
              )}
              <button
                type="button"
                disabled={!canSave}
                onClick={() => saveMutation.mutate()}
                className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {saveMutation.isPending && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                )}
                マップ{gameNumber}として保存
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
