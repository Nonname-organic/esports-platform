"""add player riot and role fields

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Riot API連携用フィールド
    op.add_column("players", sa.Column("riot_puuid", sa.String(78), nullable=True, unique=True))
    op.add_column("players", sa.Column("riot_gamename", sa.String(50), nullable=True))
    op.add_column("players", sa.Column("riot_tagline", sa.String(10), nullable=True))

    # ロール設定
    op.add_column("players", sa.Column("main_role", sa.String(50), nullable=True))
    op.add_column("players", sa.Column("sub_roles", postgresql.JSONB(), nullable=True))

    # Discord連携
    op.add_column("players", sa.Column("discord_id", sa.String(100), nullable=True))

    # インデックス
    op.create_index("idx_players_riot_puuid", "players", ["riot_puuid"], unique=True,
                    postgresql_where=sa.text("riot_puuid IS NOT NULL"))
    op.create_index("idx_players_game", "players", ["game"])


def downgrade() -> None:
    op.drop_index("idx_players_game", "players")
    op.drop_index("idx_players_riot_puuid", "players")
    op.drop_column("players", "discord_id")
    op.drop_column("players", "sub_roles")
    op.drop_column("players", "main_role")
    op.drop_column("players", "riot_tagline")
    op.drop_column("players", "riot_gamename")
    op.drop_column("players", "riot_puuid")
