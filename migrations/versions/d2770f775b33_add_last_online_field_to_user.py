"""Add last_online field to User

Revision ID: d2770f775b33
Revises: 58211f62790d
Create Date: 2022-08-08 08:40:26.744182+00:00

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "d2770f775b33"
down_revision = "58211f62790d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("user", sa.Column("last_online", sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "last_online")
    # ### end Alembic commands ###