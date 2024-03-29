"""Add columns to UserStats

Revision ID: 3cdbabb28a81
Revises: 38dcb9872b22
Create Date: 2022-11-13 20:41:53.345753+00:00

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "3cdbabb28a81"
down_revision = "38dcb9872b22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "userstats",
        sa.Column(
            "matches_played_field", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "userstats",
        sa.Column(
            "matches_played_command", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "userstats",
        sa.Column(
            "matches_won_field", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "userstats",
        sa.Column(
            "matches_won_command", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.drop_column("userstats", "matches_played")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "userstats",
        sa.Column("matches_played", sa.INTEGER(), nullable=False, server_default="0"),
    )
    op.drop_column("userstats", "matches_won_command")
    op.drop_column("userstats", "matches_won_field")
    op.drop_column("userstats", "matches_played_command")
    op.drop_column("userstats", "matches_played_field")
    # ### end Alembic commands ###
