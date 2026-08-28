/**
 * VALORANTのゲーム内定数。
 *
 * パッチごとに増えるため、複数箇所で重複定義するとズレる。参照する画面は
 * すべてここを見る。
 */

export const VALORANT_AGENTS: { role: string; agents: string[] }[] = [
  { role: "Duelist",    agents: ["Jett", "Raze", "Reyna", "Phoenix", "Yoru", "Neon", "Iso", "Waylay"] },
  { role: "Initiator",  agents: ["Sova", "Breach", "Skye", "KAY/O", "Fade", "Gekko", "Tejo"] },
  { role: "Controller", agents: ["Brimstone", "Viper", "Omen", "Astra", "Harbor", "Clove"] },
  { role: "Sentinel",   agents: ["Sage", "Cypher", "Killjoy", "Chamber", "Deadlock", "Vyse", "Veto"] },
];

/** ロール分類を除いた全エージェント名（セレクター用） */
export const ALL_VALORANT_AGENTS: string[] = VALORANT_AGENTS.flatMap((g) => g.agents);

// ── ランク ────────────────────────────────────────────────────────────────────

/** division を持つティア（Radiant のみ細分なし） */
export const RANK_TIERS = [
  "Iron", "Bronze", "Silver", "Gold",
  "Platinum", "Diamond", "Ascendant", "Immortal",
] as const;

/**
 * 選択可能なランク一覧（昇順）。
 * Radiant 以外は 1〜3 の division 付きで、全25段階。
 */
export const VALORANT_RANKS: string[] = [
  ...RANK_TIERS.flatMap((tier) => [1, 2, 3].map((d) => `${tier} ${d}`)),
  "Radiant",
];

/** ティアごとの表示色（division は同色） */
export const RANK_TIER_COLORS: Record<string, string> = {
  Iron: "text-slate-400",
  Bronze: "text-amber-600",
  Silver: "text-slate-300",
  Gold: "text-yellow-400",
  Platinum: "text-cyan-300",
  Diamond: "text-purple-400",
  Ascendant: "text-green-400",
  Immortal: "text-red-400",
  Radiant: "text-yellow-300",
};

/**
 * ランク表記からティア名を取り出す（"Diamond 2" → "Diamond"）。
 * division なしの旧データ（"Diamond"）もそのまま通る。
 */
export function rankTier(rank: string | null | undefined): string {
  return (rank ?? "").split(" ")[0];
}

/** ランクの表示色を引く。未知の表記は控えめなグレー */
export function rankColor(rank: string | null | undefined): string {
  return RANK_TIER_COLORS[rankTier(rank)] ?? "text-slate-400";
}
