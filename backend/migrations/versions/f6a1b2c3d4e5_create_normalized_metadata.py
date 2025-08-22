"""Create normalized agent metadata tables

Revision ID: f6a1b2c3d4e5
Revises: f5291c6257fc
Create Date: 2025-08-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision: str = "f6a1b2c3d4e5"
down_revision: Union[str, None] = "f5291c6257fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create template suites table
    op.create_table(
        'template_suites',
        sa.Column('id', sa.String(length=255), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create agent templates table
    op.create_table(
        'agent_templates',
        sa.Column('id', sa.String(length=255), primary_key=True),
        sa.Column('suite_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('config', sa.JSON, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_agent_templates_suite_id',
        'agent_templates', 'template_suites',
        ['suite_id'], ['id'],
        ondelete='CASCADE'
    )

    # Drop old agent_metadata table if it exists
    # Use a conditional check that works with Alembic
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'agent_metadata' in tables:
        op.drop_table('agent_metadata')

    op.create_table(
        'agent_metadata',
        sa.Column('agent_id', sa.String(length=255), primary_key=True),
        sa.Column('template_id', sa.String(length=255), nullable=True),
        sa.Column('custom_metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add foreign key constraint for template_id
    op.create_foreign_key(
        'fk_agent_metadata_template_id',
        'agent_metadata', 'agent_templates',
        ['template_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create performance indexes
    op.create_index('idx_template_suites_category', 'template_suites', ['category'])
    op.create_index('idx_agent_templates_suite', 'agent_templates', ['suite_id'])
    op.create_index('idx_agent_metadata_template', 'agent_metadata', ['template_id'])

    # Auto-populate templates from YAML files
    print("🔄 Auto-populating templates from YAML files...")
    try:
        import yaml
        from pathlib import Path

        # Get the template directory path
        backend_dir = Path(__file__).parent.parent.parent
        templates_dir = backend_dir / "agent_templates"

        if not templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        # Load YAML files directly without importing template_loader
        suites_data = {}
        templates_data = {}

        for yaml_file in templates_dir.glob("*.yaml"):
            print(f"Loading template from: {yaml_file}")

            with open(yaml_file, 'r') as f:
                suite_config = yaml.safe_load(f)

            suite_id = yaml_file.stem
            suites_data[suite_id] = suite_config

            # Extract templates from the suite
            for template_id, template_config in suite_config.get("templates", {}).items():
                templates_data[template_id] = template_config

        print(f"📁 Found {len(suites_data)} suites with {len(templates_data)} templates")

        # Populate template_suites
        for suite_id, suite_config in suites_data.items():
            suite_name = suite_config.get("name", suite_id)
            category = suite_config.get("category", "uncategorized")
            description = suite_config.get("description", f"Auto-imported suite: {suite_id}")

            # Escape single quotes for SQL
            suite_name = suite_name.replace("'", "''")
            description = description.replace("'", "''")

            op.execute(f"""
                INSERT INTO template_suites (id, name, category, description)
                VALUES ('{suite_id}', '{suite_name}', '{category}', '{description}')
                ON CONFLICT (id) DO NOTHING
            """)
            print(f"   ✅ Added suite: {suite_id} ({suite_name})")

        # Populate agent_templates
        for template_id, template_config in templates_data.items():
            # Find which suite this template belongs to
            suite_id = None
            for s_id, s_config in suites_data.items():
                if template_id in s_config.get("templates", {}):
                    suite_id = s_id
                    break

            if not suite_id:
                print(f"   ⚠️  Warning: Template '{template_id}' has no suite, skipping")
                continue

            template_name = template_config.get('name', template_id)
            description = f"Auto-imported template: {template_id}"

            # Escape single quotes for SQL
            template_name = template_name.replace("'", "''")
            description = description.replace("'", "''")

            op.execute(f"""
                INSERT INTO agent_templates (id, suite_id, name, description, config)
                VALUES ('{template_id}', '{suite_id}', '{template_name}', '{description}', '{{}}')
                ON CONFLICT (id) DO NOTHING
            """)
            print(f"   ✅ Added template: {template_id} ({template_name}) -> {suite_id}")

        print("🎉 Templates auto-populated successfully!")

    except Exception as e:
        print(f"⚠️  Warning: Could not auto-populate templates: {e}")
        print("   Templates can be populated manually later if needed")
        # Don't fail the migration if template loading fails


def downgrade() -> None:
    # Drop normalized tables
    op.drop_table('agent_metadata')
    op.drop_table('agent_templates')
    op.drop_table('template_suites')

    # Recreate old denormalized table for rollback
    op.create_table(
        'agent_metadata',
        sa.Column('agent_id', sa.String(length=255), primary_key=True),
        sa.Column('template_id', sa.String(length=255), nullable=True),
        sa.Column('template_name', sa.String(length=255), nullable=True),
        sa.Column('suite_id', sa.String(length=255), nullable=True),
        sa.Column('suite_name', sa.String(255), nullable=True),
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
