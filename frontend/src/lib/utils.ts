import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 画面に出す日時は日本時間に固定する。
 *
 * API は日時を必ず Z 付きで返し、DB 側も日時列は全て timestamptz なので、
 * 入力の解釈がぶれることはない。ぶれるのは出力側で、timeZone を省くと
 * Server Component ではコンテナの UTC、Client Component では閲覧者の
 * ローカル時刻で書き出され、同じ画面の中で9時間ずれる。
 *
 * ここで時間の足し引きは一切しない。UTC の瞬間を Intl に渡して JST で
 * 書かせるだけなので、二重変換は起こらない。
 */
const JST = "Asia/Tokyo";

function toDate(date: string | Date): Date {
  return typeof date === "string" ? new Date(date) : date;
}

/**
 * JST での年月日時分を取り出す。
 *
 * hourCycle は明示する。省くと環境によって深夜0時が 24:00 になる。
 */
function jstParts(date: string | Date): Record<"year" | "month" | "day" | "hour" | "minute", string> {
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: JST,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(toDate(date));
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return {
    year: get("year"),
    month: get("month"),
    day: get("day"),
    hour: get("hour"),
    minute: get("minute"),
  };
}

/** 「2026年8月25日 00:47」。日時を出す既定の形。 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "未定";
  return toDate(date).toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: JST,
  });
}

/** 「8/25 0:47」。年を出す余裕がない欄で使う。 */
export function formatDateShort(date: string | Date | null | undefined): string {
  if (!date) return "未定";
  const { month, day, hour, minute } = jstParts(date);
  return `${Number(month)}/${Number(day)} ${Number(hour)}:${minute}`;
}

/** 「0:47」。同じ日の中の時刻だけを出す欄で使う。 */
export function formatTime(date: string | Date | null | undefined): string {
  if (!date) return "未定";
  const { hour, minute } = jstParts(date);
  return `${Number(hour)}:${minute}`;
}

/** 日本時間で同じ日か。日付跨ぎの判定を閲覧者のTZに依存させない。 */
export function isSameDayJST(a: string | Date, b: string | Date): boolean {
  const x = jstParts(a);
  const y = jstParts(b);
  return x.year === y.year && x.month === y.month && x.day === y.day;
}

export function formatKDA(kills: number, deaths: number, assists: number): string {
  const kda = (kills + assists) / Math.max(deaths, 1);
  return kda.toFixed(2);
}

export function formatWinRate(wins: number, total: number): string {
  if (total === 0) return "0.0%";
  return `${((wins / total) * 100).toFixed(1)}%`;
}

export function formatPrize(amount: number | null, currency = "JPY"): string {
  if (!amount) return "賞金なし";
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function getGameColor(game: string): string {
  const colors: Record<string, string> = {
    VALORANT: "text-red-400 bg-red-400/10 border-red-400/30",
    LOL: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
    APEX: "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
    CS2: "text-orange-400 bg-orange-400/10 border-orange-400/30",
    OVERWATCH: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  };
  return colors[game] ?? "text-gray-400 bg-gray-400/10 border-gray-400/30";
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: "text-gray-400 bg-gray-400/10",
    registration_open: "text-green-400 bg-green-400/10",
    registration_closed: "text-yellow-400 bg-yellow-400/10",
    check_in: "text-blue-400 bg-blue-400/10",
    ongoing: "text-red-400 bg-red-400/10 animate-pulse",
    completed: "text-gray-500 bg-gray-500/10",
    cancelled: "text-gray-600 bg-gray-600/10 line-through",
  };
  return colors[status] ?? "text-gray-400 bg-gray-400/10";
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: "下書き",
    registration_open: "参加受付中",
    registration_closed: "受付終了",
    check_in: "チェックイン",
    ongoing: "開催中",
    completed: "終了",
    cancelled: "中止",
  };
  return labels[status] ?? status;
}

/**
 * 試合ステータスの表示名。
 *
 * 上の getStatusLabel は大会ステータス用（draft / registration_open …）で、
 * 試合側の scheduled / forfeit / no_show を変換できない。取り違えると
 * 内部値がそのまま画面に出るため別に持つ。
 *
 * 表記は既存UI（matches-tab / match-hero / admin の match-header）で
 * 多数を占めるものに合わせた。未知の値は元のまま返し、画面を壊さない。
 */
export function getMatchStatusLabel(status: string | null | undefined): string {
  if (!status) return "不明";
  const labels: Record<string, string> = {
    scheduled: "予定",
    ongoing: "LIVE",
    completed: "終了",
    cancelled: "中止",
    forfeit: "没収",
    no_show: "不戦敗",
  };
  return labels[status] ?? status;
}
