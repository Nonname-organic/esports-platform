"""募集投稿の種別列を広げる（player_seeks が入らず必ず 500 になっていた）

post_type は varchar(10) だったが、受け付ける値の player_seeks は 12 文字ある。
広げるだけなので既存データには影響しない。

Revision ID: 030_widen_recruitment_post_type
Revises: 029_match_result_reports
"""
import sqlalchemy as sa

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("recruitment_posts", "post_type",
                    existing_type=sa.String(10), type_=sa.String(20), existing_nullable=False)


def downgrade() -> None:
    # player_seeks の行が残っていると縮められないため、その場合は先に退避・削除が必要
    op.alter_column("recruitment_posts", "post_type",
                    existing_type=sa.String(20), type_=sa.String(10), existing_nullable=False)
