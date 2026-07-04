"""PreferenceService — 通知設定の唯一の SSOT（機能③ / ADR-0010）。

- prefs(JSONB) の構造・キー・デフォルト・precedence を知るのは本サービスだけ。
- 外部へ公開するのは正規化 DTO（PreferencesDTO）と `is_enabled(...)` のみ。
  Dispatcher / Provider / Router / UI は JSONB を直接触らない。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preference import NotificationPreference

# カテゴリは Notification Matrix 由来（Matrix が源）。チャネルは ChannelRegistry と一致。
CATEGORIES: tuple[str, ...] = ("tournament", "team", "scout", "match")
CHANNELS: tuple[str, ...] = ("browser", "email", "discord")

# デフォルト: 明示設定が無いものは ON（後方互換）。email も既定 ON だが Provider が未設定なら no-op。
_DEFAULT = True


def decide(raw: dict, category: str, channel: str) -> bool:
    """precedence を内包した純判定関数（DB非依存・テスト可能）。

    global channel OFF > (per-entity mute: 将来) > category OFF > default ON。
    """
    if (raw.get("channels", {}) or {}).get(channel, _DEFAULT) is False:
        return False
    if (raw.get("categories", {}) or {}).get(category, _DEFAULT) is False:
        return False
    return True


@dataclass
class PreferencesDTO:
    """外部（API/UI）へ渡す正規化表現。DBの生JSONBではない。"""
    channels: dict[str, bool] = field(default_factory=dict)
    categories: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"channels": self.channels, "categories": self.categories}


class PreferenceService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── 取得 ─────────────────────────────────────────────────────────────
    async def _load_raw(self, user_id: uuid.UUID) -> dict:
        row = await self._db.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return (row.prefs if row else {}) or {}

    async def get_preferences(self, user_id: uuid.UUID) -> PreferencesDTO:
        """全カテゴリ/チャネルを既定値で埋めた DTO を返す（未設定は default ON）。"""
        raw = await self._load_raw(user_id)
        raw_ch = raw.get("channels", {}) or {}
        raw_cat = raw.get("categories", {}) or {}
        return PreferencesDTO(
            channels={c: bool(raw_ch.get(c, _DEFAULT)) for c in CHANNELS},
            categories={c: bool(raw_cat.get(c, _DEFAULT)) for c in CATEGORIES},
        )

    # ── 更新（部分更新） ─────────────────────────────────────────────────
    async def update_preferences(
        self, user_id: uuid.UUID,
        *, channels: dict[str, bool] | None = None, categories: dict[str, bool] | None = None,
    ) -> PreferencesDTO:
        """既知キーのみ受理して部分更新（未知キーは無視 = スキーマ汚染防止）。commit は呼び出し側。"""
        row = await self._db.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        if row is None:
            row = NotificationPreference(user_id=user_id, prefs={})
            self._db.add(row)

        prefs = dict(row.prefs or {})
        cur_ch = dict(prefs.get("channels", {}) or {})
        cur_cat = dict(prefs.get("categories", {}) or {})
        if channels:
            for k, v in channels.items():
                if k in CHANNELS:
                    cur_ch[k] = bool(v)
        if categories:
            for k, v in categories.items():
                if k in CATEGORIES:
                    cur_cat[k] = bool(v)
        prefs["channels"] = cur_ch
        prefs["categories"] = cur_cat
        row.prefs = prefs
        # JSONB 変更を確実に検知させる（in-place 変更対策）
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(row, "prefs")
        await self._db.flush()
        return await self.get_preferences(user_id)

    # ── 判定（唯一の配信判定窓口・precedence を内包） ────────────────────
    async def is_enabled(self, user_id: uuid.UUID, category: str, channel: str) -> bool:
        """配信可否の唯一の判定窓口。precedence は decide() に内包。"""
        raw = await self._load_raw(user_id)
        return decide(raw, category, channel)
