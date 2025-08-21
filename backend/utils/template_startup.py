"""
Template auto-population utility for startup.

This module ensures that templates are automatically loaded from YAML files
into the database when the backend starts, if they're not already there.
"""

from sqlalchemy import select

from ..database import AsyncSessionLocal
from ..models import AgentTemplate, TemplateSuite
from .logging_config import get_logger
from .template_loader import load_all_templates_from_directory

logger = get_logger(__name__)


async def ensure_templates_populated():
    """
    Ensure templates are populated in the database from YAML files.
    This runs at startup and only populates if tables are empty.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Check if templates already exist
            result = await session.execute(select(TemplateSuite))
            existing_suites = result.scalars().all()

            if existing_suites:
                logger.info(
                    f"Templates already populated: {len(existing_suites)} suites found"
                )
                return

            logger.info("🔄 Auto-populating templates from YAML files...")

            # Load templates from YAML files
            suites_data, templates_data = load_all_templates_from_directory()
            logger.info(
                f"📁 Found {len(suites_data)} suites with {len(templates_data)} templates"
            )

            # Populate template_suites
            suite_count = 0
            for suite_id, suite_config in suites_data.items():
                suite = TemplateSuite(
                    id=suite_id,
                    name=suite_config.get("name", suite_id),
                    category=suite_config.get("category", "uncategorized"),
                    description=suite_config.get(
                        "description", f"Auto-imported suite: {suite_id}"
                    ),
                    icon=suite_config.get("icon"),
                )
                session.add(suite)
                suite_count += 1
                logger.info(f"   ✅ Added suite: {suite_id} ({suite.name})")

            # Populate agent_templates
            template_count = 0
            for template_id, template_config in templates_data.items():
                # Find which suite this template belongs to
                suite_id = None
                for s_id, s_config in suites_data.items():
                    if template_id in s_config.get("templates", {}):
                        suite_id = s_id
                        break

                if not suite_id:
                    logger.warning(f"Template '{template_id}' has no suite, skipping")
                    continue

                template = AgentTemplate(
                    id=template_id,
                    suite_id=suite_id,
                    name=getattr(template_config, "name", template_id),
                    description=f"Auto-imported template: {template_id}",
                    config={},
                )
                session.add(template)
                template_count += 1
                logger.info(
                    f"   ✅ Added template: {template_id} ({template.name}) -> {suite_id}"
                )

            await session.commit()
            logger.info(
                f"🎉 Successfully auto-populated {suite_count} suites and {template_count} templates!"
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error auto-populating templates: {e}")
            # Don't raise - let the app continue without templates
