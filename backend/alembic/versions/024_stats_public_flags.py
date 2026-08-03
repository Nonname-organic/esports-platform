"""teams/players に stats_public フラグ追加（傾向分析の公開制御 / デフォルト公開）

第1層（大会結果・ランキング）は常に公開でこのフラグの対象外。
第2層（マップ別勝率・構成・個人詳細スタッツ等の傾向分析）のみ本フラグで制御する。
非公開でもプラットフォーム全体の匿名集計には算入され続ける。

Revision ID: 024
Revises: 023
Create Date: 2026-08-03 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "teams",
        sa.Column("stats_public", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "players",
        sa.Column("stats_public", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("players", "stats_public")
    op.drop_column("teams", "stats_public")
