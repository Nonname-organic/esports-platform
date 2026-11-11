"""大会の公開設定を rules から visibility 列へ写す

作成画面は公開設定を rules.visibility にだけ入れて送っており、
visibility 列は既定の public のまま保存されていた。一覧・検索・ホームは
列を見るため、「非公開」「限定公開」を選んだ大会も一般に表示されていた。

作成後に編集画面で保存した大会は列と rules が一致しているので、
列が public のまま rules だけが limited / private の行に限って直す。

書き換える前の値は tournament_visibility_backup_028 に残す。downgrade は
この表から戻すが、移行後に主催者が公開設定を変えた行には触れない。
表は復旧の根拠として upgrade 後も残す（不要になったら別の版で消す）。

Revision ID: 028_sync_tournament_visibility
Revises: 027_valorant_maps
"""
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None

BACKUP = "tournament_visibility_backup_028"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BACKUP} (
            tournament_id uuid PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
            previous_visibility varchar(20) NOT NULL,
            new_visibility varchar(20) NOT NULL,
            migrated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO {BACKUP} (tournament_id, previous_visibility, new_visibility)
        SELECT id, visibility, rules->>'visibility'
          FROM tournaments
         WHERE visibility = 'public'
           AND rules->>'visibility' IN ('limited', 'private')
        ON CONFLICT (tournament_id) DO NOTHING
        """
    )
    op.execute(
        f"""
        UPDATE tournaments t
           SET visibility = b.new_visibility
          FROM {BACKUP} b
         WHERE b.tournament_id = t.id
           AND t.visibility = b.previous_visibility
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE tournaments t
           SET visibility = b.previous_visibility
          FROM {BACKUP} b
         WHERE b.tournament_id = t.id
           AND t.visibility = b.new_visibility
        """
    )
    op.execute(f"DROP TABLE IF EXISTS {BACKUP}")
