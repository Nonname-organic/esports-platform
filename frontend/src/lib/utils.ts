import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "未定";
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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
