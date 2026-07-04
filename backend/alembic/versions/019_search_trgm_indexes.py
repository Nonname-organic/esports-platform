"""enable pg_trgm + GIN indexes for global search (ADR-0013)

Revision ID: 019
Revises: 018
Create Date: 2026-07-05 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_teams_name_trgm ON teams USING gin (name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_players_ign_trgm ON players USING gin (in_game_name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tournaments_name_trgm ON tournaments USING gin (name gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tournaments_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_players_ign_trgm")
    op.execute("DROP INDEX IF EXISTS ix_teams_name_trgm")
    # 拡張は他機能が使う可能性があるため残す
