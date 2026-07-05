import { Shield, ShieldHalf, Gem, Crown } from "lucide-react";
import { cn } from "@/lib/utils";

/** Tier アイコン（backend の tier icon キーに対応）。 */
const ICONS: Record<string, React.ElementType> = {
  shield: Shield,
  "shield-half": ShieldHalf,
  gem: Gem,
  crown: Crown,
};

function tierKeyToIcon(key?: string): string {
  if (key === "master" || key === "grandmaster") return "crown";
  if (key === "platinum" || key === "diamond") return "gem";
  if (key === "gold") return "shield-half";
  return "shield";
}

/**
 * ランク Tier バッジ（再利用可能 / チーム・プレイヤー共通）。
 * 受け取るのは Tier（key/label/color）と Progress のみ。数値しきい値は持たない（SSOTはBackend）。
 * - variant="pill": 行内バッジ
 * - variant="ring": Progress Ring + Tier グロー（Podium / RankCard 用）
 */
export function RankBadge({
  tierKey,
  label,
  color,
  progress = 0,
  rp,
  size = "md",
  variant = "pill",
  className,
}: {
  tierKey?: string;
  label: string;
  color: string;
  progress?: number;
  rp?: number;
  size?: "sm" | "md" | "lg";
  variant?: "pill" | "ring";
  className?: string;
}) {
  const Icon = ICONS[tierKeyToIcon(tierKey)] ?? Shield;

  if (variant === "ring") {
    const dim = size === "lg" ? 72 : size === "sm" ? 44 : 56;
    const stroke = size === "lg" ? 5 : 4;
    const r = (dim - stroke) / 2;
    const circ = 2 * Math.PI * r;
    const clamped = Math.max(0, Math.min(1, progress));
    return (
      <span className={cn("inline-flex flex-col items-center gap-1", className)}>
        <span className="relative inline-flex items-center justify-center" style={{ width: dim, height: dim }}>
          <svg width={dim} height={dim} className="-rotate-90">
            <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
            <circle
              cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
              strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ * (1 - clamped)}
            />
          </svg>
          <Icon
            className="absolute"
            style={{ color, width: dim * 0.42, height: dim * 0.42, filter: `drop-shadow(0 0 8px ${color}aa)` }}
          />
        </span>
        <span className="text-[11px] font-black tracking-wide" style={{ color }}>{label}</span>
      </span>
    );
  }

  const pad = size === "lg" ? "px-3 py-1.5 text-sm" : size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";
  const iconSize = size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5";
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded-full border font-black tracking-wide", pad, className)}
      style={{ color, borderColor: `${color}55`, backgroundColor: `${color}1a` }}
    >
      <Icon className={iconSize} />
      {label}
      {rp != null && <span className="font-bold opacity-80">· {rp.toLocaleString()} RP</span>}
    </span>
  );
}
