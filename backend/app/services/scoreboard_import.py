"""
スコアボード画像の解析結果を、試合に参加している選手へ紐付ける。

OCRの読み取り結果はそのまま保存せず、必ず運営が確認・修正できる「プレビュー」
として返す。照合候補は該当試合の2チームの登録選手のみに絞られるため、多少の
誤読があっても正しい選手に寄せられる。
"""
from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import NotFoundError
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team, TeamMember
from app.services import scoreboard_ocr

# この類似度を下回る候補は「未確定」として運営に選ばせる
_NAME_MATCH_THRESHOLD = 0.55


@dataclass
class RosterEntry:
    player_id: uuid.UUID
    team_id: uuid.UUID
    display_name: str
    # 照合に使う表記のゆらぎ（IGN / Riot ID / 実名）
    aliases: list[str]


def _normalize_name(value: str) -> str:
    """OCR誤読に強い形へ正規化する（記号除去・小文字化）。"""
    lowered = value.strip().lower()
    # Riot IDのタグ(#XXX)はスコアボードでは表示されない
    lowered = lowered.split("#", 1)[0]
    return re.sub(r"[^0-9a-z぀-ヿ一-鿿]", "", lowered)


def _name_variants(ocr_name: str) -> list[str]:
    """
    スコアボードの表示名から照合候補を作る。

    "SKS|ばった" のようにチームタグ付きで表示されるため、区切り文字より後ろの
    部分も候補に含める。登録側は素の選手名であることが多い。
    """
    variants = [ocr_name]
    for separator in ("|", "｜", "/", "／"):
        if separator in ocr_name:
            variants.append(ocr_name.rsplit(separator, 1)[-1])
    return [v for v in (s.strip() for s in variants) if v]


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
        self,
        ocr_name: str,
        roster: list[RosterEntry],
        used: set[uuid.UUID],
        preferred_team: Optional[uuid.UUID],
    ) -> tuple[Optional[RosterEntry], float]:
        """OCR名に最も近い未使用の選手を返す。"""
        variants = [_normalize_name(v) for v in _name_variants(ocr_name)]
        variants = [v for v in variants if v]
        if not variants:
            return None, 0.0

        best_entry, best_score = None, 0.0
        for entry in roster:
            if entry.player_id in used:
                continue
            score = max(
                _similarity(variant, _normalize_name(alias))
                for alias in entry.aliases
                for variant in variants
            )
            # 行の背景色から推定したチームと一致する候補をわずかに優遇する
            if preferred_team is not None and entry.team_id == preferred_team:
                score += 0.05
            if score > best_score:
                best_entry, best_score = entry, score

        if best_score < _NAME_MATCH_THRESHOLD:
            return None, min(best_score, 1.0)
        return best_entry, min(best_score, 1.0)

    def _resolve_team_hints(
        self, rows: list, roster: list[RosterEntry], match: Match
    ) -> dict[str, uuid.UUID]:
        """
        行の背景色（red/green）が実際のどちらのチームかを対応付ける。

        スコアボードは成績順に並ぶため色だけが画像側の手がかりになる。まず名前で
        確実に照合できた行を使って色とチームの対応を多数決で決め、残りの行の
        照合に利用する。
        """
        votes: dict[str, Counter] = {}
        used: set[uuid.UUID] = set()
        for row in rows:
            if not row.team_hint:
                continue
            entry, score = self._match_player(row.name, roster, used, None)
            if entry is None or score < 0.85:
                continue
            used.add(entry.player_id)
            votes.setdefault(row.team_hint, Counter())[entry.team_id] += 1

        resolved: dict[str, uuid.UUID] = {}
        for hint, counter in votes.items():
            resolved[hint] = counter.most_common(1)[0][0]

        # 2色とも判明していない場合、残りの色は相手チームに割り当てる
        team_ids = [tid for tid in (match.team1_id, match.team2_id) if tid]
        if len(resolved) == 1 and len(team_ids) == 2:
            known_hint, known_team = next(iter(resolved.items()))
            other_team = next(t for t in team_ids if t != known_team)
            other_hint = "green" if known_hint == "red" else "red"
            resolved[other_hint] = other_team
        return resolved

    async def parse(self, match_id: uuid.UUID, image: bytes) -> dict:
        match = await self._db.get(Match, match_id)
        if not match:
            raise NotFoundError("試合", str(match_id))

        # OCRは1枚あたり10秒以上かかるCPU処理。await せずに直接呼ぶと
        # イベントループを占有し、その間APIサーバー全体が応答しなくなるため
        # 必ずスレッドプールへ逃がす
        parsed, _img = await run_in_threadpool(scoreboard_ocr.parse_scoreboard, image)
        roster = await self._load_roster(match)
        warnings = list(parsed.warnings)
        if not roster:
            warnings.append(
                "この試合のチームに登録選手がいないため、選手の自動紐付けができません"
            )

        hint_to_team = self._resolve_team_hints(parsed.rows, roster, match)

        used: set[uuid.UUID] = set()
        rows: list[dict] = []
        for row in parsed.rows:
            preferred = hint_to_team.get(row.team_hint or "")
            entry, score = self._match_player(row.name, roster, used, preferred)
            if entry is not None:
                used.add(entry.player_id)

            rows.append(
                {
                    "ocr_name": row.name,
                    "player_id": str(entry.player_id) if entry else None,
                    "player_name": entry.display_name if entry else None,
                    "team_id": str(entry.team_id)
                    if entry
                    else (str(preferred) if preferred else None),
                    "match_confidence": round(score, 3),
                    "agent": row.agent,
                    "acs": row.acs,
                    "kills": row.kills,
                    "deaths": row.deaths,
                    "assists": row.assists,
                    "first_bloods": row.first_bloods,
                    "missing": row.missing,
                }
            )

        unmatched = [r["ocr_name"] for r in rows if r["player_id"] is None]
        if unmatched:
            warnings.append(
                f"{len(unmatched)}名の選手を自動で特定できませんでした"
                f"（{', '.join(unmatched)}）。手動で選択してください"
            )

        return {
            "rows": rows,
            "warnings": warnings,
            "detected_score": (
                list(parsed.detected_score) if parsed.detected_score else None
            ),
            "teams": await self._load_team_options(match, roster),
        }

    async def _load_team_options(
        self, match: Match, roster: list[RosterEntry]
    ) -> list[dict]:
        """プレビュー画面で選手を手動選択するための候補一覧。"""
        team_ids = [tid for tid in (match.team1_id, match.team2_id) if tid]
        if not team_ids:
            return []

        teams = (
            (await self._db.execute(select(Team).where(Team.id.in_(team_ids))))
            .scalars()
            .all()
        )

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
