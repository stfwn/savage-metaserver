"""Replace is_admin field with rank on UserClanLink

Revision ID: 3b6a2db249ae
Revises: db0fca856f9d
Create Date: 2022-09-17 12:41:48.119076+00:00

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlmodel import Session


# revision identifiers, used by Alembic.
revision = "3b6a2db249ae"
down_revision = "db0fca856f9d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "userclanlink",
        sa.Column("rank", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    with Session(op.get_context().connection) as session:
        session.exec("UPDATE userclanlink SET rank = 'owner' WHERE is_admin = TRUE;")
        session.exec("UPDATE userclanlink SET rank = 'member' WHERE is_admin = FALSE;")
    op.drop_column("userclanlink", "is_admin")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("userclanlink", sa.Column("is_admin", sa.BOOLEAN(), nullable=True))
    op.drop_column("userclanlink", "rank")
    # ### end Alembic commands ###
