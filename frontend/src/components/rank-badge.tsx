import { Shield, ShieldHalf, Gem, Crown } from "lucide-react";
import { cn } from "@/lib/utils";

/** Tier アイコン（backend の icon キーと対応）。 */
const ICONS: Record<string, React.ElementType> = {
  shield: Shield,
  "shield-half": ShieldHalf,
  gem: Gem,
  crown: Crown,
};

/**
 * ランク Tier バッジ（再利用可能 / チーム・プレイヤー共通）。
 * 色は backend の tier_color（SSOT）をそのまま使用。
 */
export function RankBadge({
  tierKey,
  label,
  color,
  rp,
  size = "md",
  className,
}: {
  tierKey?: string;
  label: string;
  color: string;
  rp?: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const Icon = (tierKey && ICONS[tierKeyToIcon(tierKey)]) || Shield;
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

// tierKey → icon（backend の icon を持たない呼び出し向けの簡易対応）
function tierKeyToIcon(key: string): string {
  if (key === "master" || key === "grandmaster") return "crown";
  if (key === "platinum" || key === "diamond") return "gem";
  if (key === "gold") return "shield-half";
  return "shield";
}
