"""
Player schemas - Riot API連携を考慮した設計

将来的なRiot API統合:
- riot_puuid: Riot APIの永続的ユーザー識別子
- riot_gamename/riot_tagline: Riot ID構成要素
- 登録時にName#TAGを入力 → 将来的にRiot APIで検証・PUUID取得
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── ゲーム別ロール定義 ─────────────────────────────────────────────────────────
GAME_ROLES: dict[str, list[str]] = {
    "VALORANT": ["Duelist", "Sentinel", "Initiator", "Controller"],
    "LOL": ["Top", "Jungle", "Mid", "ADC", "Support"],
    "APEX": ["Assault", "Recon", "Skirmisher", "Controller", "Support"],
    "CS2": ["Entry Fragger", "AWPer", "Support", "Lurker", "IGL"],
    "OVERWATCH": ["Tank", "Damage", "Support"],
}


class RiotIdInput(BaseModel):
    """Riot ID（Name#TAG形式）入力の検証"""
    riot_id: str = Field(..., description="Riot ID (例: SEN Tenz#NA1 または 名前#タグ)")

    @field_validator("riot_id")
    @classmethod
    def validate_riot_id(cls, v: str) -> str:
        if "#" in v:
            parts = v.split("#", 1)
            if len(parts[0]) < 1 or len(parts[1]) < 1:
                raise ValueError("Riot IDの形式が正しくありません（例: Name#TAG）")
        return v

    def parse(self) -> tuple[str, Optional[str], Optional[str]]:
        """(in_game_name, gamename, tagline) を返す"""
        if "#" in self.riot_id:
            gamename, tagline = self.riot_id.split("#", 1)
            return self.riot_id, gamename.strip(), tagline.strip()
        return self.riot_id, None, None


class PlayerCreate(BaseModel):
    # 必須
    game: str = Field(..., description="ゲーム種別")
    riot_id: str = Field(..., min_length=1, max_length=111, description="Riot ID または IGN（Name#TAG形式推奨）")

    # ロール
    main_role: Optional[str] = Field(None, max_length=50, description="メインロール")
    sub_roles: Optional[list[str]] = Field(default_factory=list, description="サブロール一覧")

    # プロフィール
    discord_id: Optional[str] = Field(None, max_length=100)
    agent_pool: Optional[list[str]] = Field(default_factory=list, description="使用エージェント一覧")
    rank: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    real_name: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=50)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    twitch_handle: Optional[str] = Field(None, max_length=100)


class PlayerUpdate(BaseModel):
    riot_id: Optional[str] = Field(None, max_length=111)
    main_role: Optional[str] = Field(None, max_length=50)
    sub_roles: Optional[list[str]] = None
    discord_id: Optional[str] = Field(None, max_length=100)
    agent_pool: Optional[list[str]] = None
    rank: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    real_name: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=50)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    twitch_handle: Optional[str] = Field(None, max_length=100)


class PlayerSchema(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    in_game_name: str
    riot_id: Optional[str]
    riot_gamename: Optional[str]
    riot_tagline: Optional[str]
    riot_puuid: Optional[str]      # Riot API取得済みの場合のみ
    game: str
    rank: Optional[str]
    main_role: Optional[str]
    sub_roles: Optional[list]
    agent_pool: Optional[list]
    discord_id: Optional[str]
    region: Optional[str]
    nationality: Optional[str]
    real_name: Optional[str]
    bio: Optional[str]
    twitter_handle: Optional[str]
    twitch_handle: Optional[str]
    created_at: datetime
    updated_at: datetime

    # 関連情報（JOIN取得）
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    team_name: Optional[str] = None
    team_id: Optional[uuid.UUID] = None
