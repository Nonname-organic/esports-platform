"""VALORANTのマップを現行の全13種にそろえる

001 のシード時点では9種しか入れておらず、画面のマップ選択欄
（Icebox / Breeze / Corrode / Summit を含む13種）と食い違っていた。
DBに無いマップを選ぶとマップが解決できず登録に失敗するため、不足分を足す。

ランク対象かどうかはRiotの都合で頻繁に入れ替わる。ここでは
「大会で使えるマップ」としてスタンダードの13種をすべて有効にする。

Revision ID: 027_valorant_maps
Revises: 026_check_in_end_at
"""
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None

# 001 で入れた9種に対する不足分
ADDED = [
    ("icebox", "Icebox"),
    ("breeze", "Breeze"),
    ("corrode", "Corrode"),
    ("summit", "Summit"),
]


def upgrade() -> None:
    values = ",\n        ".join(
        f"(gen_random_uuid(), 'VALORANT', '{internal}', '{display}', true)"
        for internal, display in ADDED
    )
    # 環境によっては手で入れている場合があるため、重複は無視する
    op.execute(
        f"""
        INSERT INTO maps (id, game, internal_name, display_name, is_active) VALUES
        {values}
        ON CONFLICT ON CONSTRAINT uq_map_game_name DO NOTHING
        """
    )


def downgrade() -> None:
    names = ", ".join(f"'{internal}'" for internal, _ in ADDED)
    # 試合で使われていたら消さない（match_games.map_id が参照している）
    op.execute(
        f"""
        DELETE FROM maps
        WHERE game = 'VALORANT'
          AND internal_name IN ({names})
          AND id NOT IN (SELECT map_id FROM match_games WHERE map_id IS NOT NULL)
          AND id NOT IN (SELECT map_id FROM ban_picks WHERE map_id IS NOT NULL)
        """
    )
