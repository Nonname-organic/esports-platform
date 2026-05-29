"""add indexes and partitioning hints

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # updated_at の自動更新トリガー
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    for table in ["users", "players", "teams", "tournaments", "matches"]:
        op.execute(f"""
            CREATE TRIGGER trigger_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)

    # GIN インデックス: JSONB フィールドへの高速アクセス
    op.execute(
        "CREATE INDEX idx_tournaments_rules_gin ON tournaments USING GIN(rules)"
    )
    op.execute(
        "CREATE INDEX idx_pms_custom_stats_gin ON player_match_stats USING GIN(custom_stats)"
    )
    op.execute(
        "CREATE INDEX idx_agg_player_agent_gin ON agg_player_stats USING GIN(agent_breakdown)"
    )
    op.execute(
        "CREATE INDEX idx_comp_stats_composition_gin ON agg_composition_stats USING GIN(composition)"
    )

    # 複合インデックス: よく使われるフィルタリングパターン
    op.execute("""
        CREATE INDEX idx_matches_tournament_status_round
        ON matches(tournament_id, status, round_number)
    """)
    op.execute("""
        CREATE INDEX idx_registrations_tournament_status
        ON tournament_registrations(tournament_id, status)
    """)

    # 部分インデックス: アクティブなデータのみ
    op.execute("""
        CREATE INDEX idx_tournaments_active
        ON tournaments(game, start_at DESC)
        WHERE status IN ('registration_open', 'registration_closed', 'check_in', 'ongoing')
    """)
    op.execute("""
        CREATE INDEX idx_matches_upcoming
        ON matches(scheduled_at ASC)
        WHERE status = 'scheduled'
    """)
    op.execute("""
        CREATE INDEX idx_users_active
        ON users(email)
        WHERE is_active = true
    """)

    # フルテキスト検索インデックス（大会名・チーム名検索）
    op.execute("""
        ALTER TABLE tournaments ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english', coalesce(name, '')) ||
            to_tsvector('simple', coalesce(name, ''))
        ) STORED
    """)
    op.execute(
        "CREATE INDEX idx_tournaments_search ON tournaments USING GIN(search_vector)"
    )

    op.execute("""
        ALTER TABLE teams ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english', coalesce(name, '') || ' ' || coalesce(tag, ''))
        ) STORED
    """)
    op.execute(
        "CREATE INDEX idx_teams_search ON teams USING GIN(search_vector)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE teams DROP COLUMN IF EXISTS search_vector")
    op.execute("ALTER TABLE tournaments DROP COLUMN IF EXISTS search_vector")

    for table in ["users", "players", "teams", "tournaments", "matches"]:
        op.execute(f"DROP TRIGGER IF EXISTS trigger_{table}_updated_at ON {table}")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
