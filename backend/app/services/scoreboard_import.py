"""
スコアボード画像の解析結果を、試合に参加している選手へ紐付ける。

OCRの読み取り結果はそのまま保存せず、必ず運営が確認・修正できる「プレビュー」
として返す。照合候補は該当試合の2チームの登録選手のみに絞られるため、多少の
誤読があっても正しい選手に寄せられる。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.services import agent_icons, scoreboard_ocr

# この類似度を下回る候補は「未確定」として運営に選ばせる
_NAME_MATCH_THRESHOLD = 0.55


@dataclass
class RosterEntry:
    player_id: uuid.UUID
    team_id: uuid.UUID
    display_name: str
    # 照合に使う表記のゆらぎ（IGN / Riot ID / タグ付き）
    aliases: list[str]


def _normalize_name(value: str) -> str:
    """OCR誤読に強い形へ正規化する（記号除去・小文字化・全角半角の揺れ吸収）。"""
    lowered = value.strip().lower()
    # Riot IDのタグ(#XXX)はスコアボードで省略されることがあるため落とす
    lowered = lowered.split("#", 1)[0]
    return re.sub(r"[^0-9a-z぀-ヿ一-鿿]", "", lowered)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # 片方がもう片方を含む場合（チームタグ付きで表示される等）は高めに評価する
    if a in b or b in a:
        return 0.92
    return SequenceMatcher(None, a, b).ratio()


class ScoreboardImportService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _load_roster(self, match: Match) -> list[RosterEntry]:
        team_ids = [tid for tid in (match.team1_id, match.team2_id) if tid]
        if not team_ids:
            return []

        rows = (
            await self._db.execute(
                select(TeamMember, Player)
                .join(Player, Player.id == TeamMember.player_id)
                .where(
                    TeamMember.team_id.in_(team_ids),
                    TeamMember.left_at.is_(None),
                )
            )
        ).all()

        roster: list[RosterEntry] = []
        for member, player in rows:
            aliases = [player.in_game_name]
            if player.riot_gamename:
                aliases.append(player.riot_gamename)
                if player.riot_tagline:
                    aliases.append(f"{player.riot_gamename}#{player.riot_tagline}")
            if player.real_name:
                aliases.append(player.real_name)

            roster.append(
                RosterEntry(
                    player_id=player.id,
                    team_id=member.team_id,
                    display_name=player.in_game_name,
                    aliases=[a for a in aliases if a],
                )
            )
        return roster

    def _match_player(
        self, ocr_name: str, roster: list[RosterEntry], used: set[uuid.UUID]
    ) -> tuple[Optional[RosterEntry], float]:
        """OCR名に最も近い未使用の選手を返す。"""
        normalized = _normalize_name(ocr_name)
        if not normalized:
            return None, 0.0

        best_entry, best_score = None, 0.0
        for entry in roster:
            if entry.player_id in used:
                continue
            score = max(
                _similarity(normalized, _normalize_name(alias))
                for alias in entry.aliases
            )
            if score > best_score:
                best_entry, best_score = entry, score

        if best_score < _NAME_MATCH_THRESHOLD:
            return None, best_score
        return best_entry, best_score

    async def parse(
        self, match_id: uuid.UUID, image: bytes
    ) -> dict:
        match = await self._db.get(Match, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

        parsed, original = scoreboard_ocr.parse_scoreboard(image)
        roster = await self._load_roster(match)
        warnings = list(parsed.warnings)
        if not roster:
            warnings.append(
                "この試合のチームに登録選手がいないため、選手の自動紐付けができません"
            )

        agent_matching = agent_icons.is_available()
        if not agent_matching:
            warnings.append(
                "エージェントのアイコン照合が利用できないため、エージェントは手動で選択してください"
            )

        used: set[uuid.UUID] = set()
        rows: list[dict] = []
        for row in parsed.rows:
            entry, score = self._match_player(row.name, roster, used)
            if entry is not None:
                used.add(entry.player_id)

            agent = row.agent
            if agent is None and agent_matching:
                agent = agent_icons.identify_in_row(original, row.box)

            rows.append(
                {
                    "ocr_name": row.name,
                    "player_id": str(entry.player_id) if entry else None,
                    "player_name": entry.display_name if entry else None,
                    "team_id": str(entry.team_id) if entry else None,
                    "match_confidence": round(score, 3),
                    "agent": agent,
                    "acs": row.acs,
                    "kills": row.kills,
                    "deaths": row.deaths,
                    "assists": row.assists,
                    "first_bloods": row.first_bloods,
                    "ocr_confidence": row.confidence,
                }
            )

        unmatched = [r["ocr_name"] for r in rows if r["player_id"] is None]
        if unmatched:
            warnings.append(
                f"{len(unmatched)}名の選手を自動で特定できませんでした（{', '.join(unmatched)}）。手動で選択してください"
            )

        teams = await self._load_team_options(match)
        return {
            "rows": rows,
            "warnings": warnings,
            "detected_score": (
                list(parsed.detected_score) if parsed.detected_score else None
            ),
            "teams": teams,
        }

    async def _load_team_options(self, match: Match) -> list[dict]:
        """プレビュー画面で選手を手動選択するための候補一覧。"""
        team_ids = [tid for tid in (match.team1_id, match.team2_id) if tid]
        if not team_ids:
            return []

        teams = (
            await self._db.execute(select(Team).where(Team.id.in_(team_ids)))
        ).scalars().all()
        roster = await self._load_roster(match)

        by_team: dict[uuid.UUID, list[dict]] = {tid: [] for tid in team_ids}
        for entry in roster:
            by_team.setdefault(entry.team_id, []).append(
                {"id": str(entry.player_id), "name": entry.display_name}
            )

        return [
            {
                "id": str(team.id),
                "name": team.name,
                "players": by_team.get(team.id, []),
            }
            for team in teams
        ]
