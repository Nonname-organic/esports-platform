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
