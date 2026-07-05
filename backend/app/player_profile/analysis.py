"""Player AI Analysis（ADR-0018 / Read Only・Provider化）。

`PlayerAnalysisProvider` を唯一のIFとし、現段階は `RuleBasedAnalysisProvider`。
将来 OpenAI / Claude / Gemini 実装へ差し替え可能（返却DTO契約は不変）。
"""

from __future__ import annotations

from typing import Protocol

# VALORANT エージェント → ロール（recommended_role 導出用・未知はFlex）
_AGENT_ROLE: dict[str, str] = {
    **{a: "Duelist" for a in ["jett", "raze", "reyna", "phoenix", "yoru", "neon", "iso"]},
    **{a: "Controller" for a in ["brimstone", "omen", "viper", "astra", "harbor", "clove"]},
    **{a: "Initiator" for a in ["sova", "breach", "skye", "kayo", "kay/o", "fade", "gekko"]},
    **{a: "Sentinel" for a in ["killjoy", "cypher", "sage", "chamber", "deadlock", "vyse"]},
}


def _clamp(v: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(v))))


class PlayerAnalysisProvider(Protocol):
    """AI分析の唯一IF。将来 LLM 実装で差し替え可能。"""
    kind: str
    async def analyze(self, *, player: dict, career: dict) -> dict: ...


class RuleBasedAnalysisProvider:
    """career統計からルールベースでプレイスタイル/強み/弱み等を導出（保存禁止）。"""
    kind = "rule_based"

    async def analyze(self, *, player: dict, career: dict) -> dict:
        kda = float(career.get("avg_kda", 0) or 0)
        acs = float(career.get("avg_acs", 0) or 0)
        wr = float(career.get("win_rate", 0) or 0)
        kills = float(career.get("avg_kills", 0) or 0)
        assists = float(career.get("avg_assists", 0) or 0)
        matches = int(career.get("total_matches", 0) or 0)
        agents = career.get("agent_usage", []) or []

        kill_share = kills / max(kills + assists, 0.1)
        aggression = _clamp(kill_share * 70 + min(acs / 8, 30))
        consistency = _clamp(wr * 60 + min(kda, 3.0) / 3.0 * 40)

        # プレイスタイル
        if aggression >= 65:
            style = "アグレッシブ・エントリー"
        elif kill_share < 0.45:
            style = "サポート・イニシエーター"
        elif acs >= 220 and kda >= 1.2:
            style = "安定型フラッガー"
        else:
            style = "バランス型"

        # 強み / 弱み
        strengths: list[str] = []
        weaknesses: list[str] = []
        if kda >= 1.3:
            strengths.append("高いKDAで生存力・貢献度が高い")
        elif kda and kda < 0.9:
            weaknesses.append("KDAが伸び悩み、デス管理に課題")
        if acs >= 230:
            strengths.append("高い平均ACSで火力に優れる")
        elif acs and acs < 170:
            weaknesses.append("平均ACSが低く、ラウンド火力が課題")
        if wr >= 0.55:
            strengths.append("勝率が高く勝利貢献度が高い")
        elif wr and wr < 0.45:
            weaknesses.append("勝率が伸びず、勝ち筋づくりに課題")
        if matches and matches < 10:
            weaknesses.append("試合数が少なく評価サンプルが不足")

        # 得意エージェント（勝率順・最低3試合）
        eligible = [a for a in agents if (a.get("games", 0) or 0) >= 3]
        best = max(eligible, key=lambda a: (a.get("win_rate", 0), a.get("games", 0)), default=None)
        recommended_agent = best.get("agent") if best else (agents[0].get("agent") if agents else None)

        # 推奨ロール（最多起用エージェントのロール）
        top_agent = max(agents, key=lambda a: a.get("games", 0), default=None)
        recommended_role = None
        if top_agent and top_agent.get("agent"):
            recommended_role = _AGENT_ROLE.get(str(top_agent["agent"]).lower())
        if not recommended_role:
            recommended_role = player.get("main_role") or "Flex"

        if not strengths:
            strengths.append("特出した弱点が少なくバランスが取れている")
        if not weaknesses:
            weaknesses.append("さらなる試合数で強みを確立するとよい")

        summary = (
            f"{player.get('in_game_name', 'この選手')} は「{style}」タイプ。"
            f"平均KDA {kda:.2f} / ACS {acs:.0f} / 勝率 {wr*100:.0f}%。"
            f"攻撃性 {aggression} / 安定性 {consistency}。"
            + (f" 推奨ロールは {recommended_role}。" if recommended_role else "")
            + (f" 得意エージェントは {recommended_agent}。" if recommended_agent else "")
        )

        return {
            "provider": self.kind,
            "play_style": style,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommended_role": recommended_role,
            "recommended_agent": recommended_agent,
            "consistency": consistency,
            "aggression": aggression,
            "summary": summary,
        }
