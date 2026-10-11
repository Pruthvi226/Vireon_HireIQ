"""Register the existing startup-managed schema as the migration baseline."""

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing installations are initialized by app.main.init_db for SQLite compatibility.
    pass


def downgrade() -> None:
    pass