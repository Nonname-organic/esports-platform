"""tournaments.approval_mode — 参加申請の承認方式（手動 / 自動先着 / 自動抽選）

manual : 従来どおり主催者が1件ずつ承認/却下する
auto   : 申請時に先着順で自動承認し、定員に達した後の申請は補欠にする
lottery: 抽選。受付中は審査中のまま溜め、受付終了時に無作為抽選で当落を決める

Revision ID: 025
Revises: 024
Create Date: 2026-08-27 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column(
            "approval_mode",
            sa.String(20),
            nullable=False,
            server_default="manual",  # 既存大会は従来どおり手動承認
        ),
    )


def downgrade() -> None:
    op.drop_column("tournaments", "approval_mode")
