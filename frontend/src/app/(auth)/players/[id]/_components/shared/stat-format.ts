/** 統計値のフォーマット共通ユーティリティ（空データ対応） */

export const DASH = "—";

export function fmtNum(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return DASH;
  return v.toFixed(digits);
}

export function fmtInt(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return DASH;
  return Math.round(v).toLocaleString();
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return DASH;
  return `${(v * 100).toFixed(digits)}%`;
}

/** win_rate などの数値の色分け（高いほど緑） */
export function wrColor(v: number | null | undefined): string {
  if (v == null) return "text-slate-400";
  if (v >= 0.6) return "text-green-400";
  if (v >= 0.5) return "text-brand-400";
  if (v >= 0.4) return "text-slate-300";
  return "text-red-400";
}
