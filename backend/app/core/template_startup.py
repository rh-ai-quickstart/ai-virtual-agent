"""
Template auto-population utility for startup.

This module ensures that templates are automatically loaded from YAML files
into the database when the backend starts.  New suites and templates
discovered in YAML that are not yet in the database are added
incrementally so that adding a new YAML file does not require a
database wipe.
"""

import logging
import uuid

from sqlalchemy import select

from ..database import AsyncSessionLocal
from ..models import AgentTemplate, TemplateSuite
from .template_loader import load_all_templates_from_directory

logger = logging.getLogger(__name__)


async def ensure_templates_populated():
    """
    Ensure templates are populated in the database from YAML files.
    Performs an incremental sync: any suites or templates present in
    YAML but missing from the database are inserted.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Load templates from YAML files
            suites_data, templates_data = load_all_templates_from_directory()
            logger.info(
                f"📁 Found {len(suites_data)} suites with "
                f"{len(templates_data)} templates in YAML"
            )

            # Build a lookup of existing suites by name
            result = await session.execute(select(TemplateSuite))
            existing_suites = {s.name: s for s in result.scalars().all()}

            # Build a lookup of existing templates by name
            result = await session.execute(select(AgentTemplate))
            existing_templates = {t.name: t for t in result.scalars().all()}

            suite_id_mapping = {}  # YAML suite key -> UUID (existing or new)
            suite_count = 0
            template_count = 0

            # Sync suites
            for suite_key, suite_config in suites_data.items():
                suite_name = suite_config.get("name", suite_key)
                if suite_name in existing_suites:
                    suite_id_mapping[suite_key] = existing_suites[suite_name].id
                    continue

                suite_uuid = uuid.uuid4()
                suite_id_mapping[suite_key] = suite_uuid
                suite = TemplateSuite(
                    id=suite_uuid,
                    name=suite_name,
                    category=suite_config.get("category", "uncategorized"),
                    description=suite_config.get(
                        "description", f"Auto-imported suite: {suite_key}"
                    ),
                    icon=suite_config.get("icon"),
                )
                session.add(suite)
                suite_count += 1
                logger.info(f"   ✅ Added suite: {suite_key} ({suite.name})")

            # Sync templates
            for template_key, template_config in templates_data.items():
                template_name = getattr(template_config, "name", template_key)
                if template_name in existing_templates:
                    continue

                # Find which suite this template belongs to
                suite_key = None
                for s_key, s_config in suites_data.items():
                    if template_key in s_config.get("templates", {}):
                        suite_key = s_key
                        break

                if not suite_key:
                    logger.warning(f"Template '{template_key}' has no suite, skipping")
                    continue

                template_uuid = uuid.uuid4()
                suite_uuid = suite_id_mapping[suite_key]
                template = AgentTemplate(
                    id=template_uuid,
                    suite_id=suite_uuid,
                    name=template_name,
                    description=f"Auto-imported template: {template_key}",
                    config={},
                )
                session.add(template)
                template_count += 1
                logger.info(
                    f"   ✅ Added template: {template_key} ({template.name}) -> "
                    f"{suite_key}"
                )

            if suite_count or template_count:
                await session.commit()
                logger.info(
                    f"🎉 Synced {suite_count} new suites and "
                    f"{template_count} new templates!"
                )
            else:
                logger.info("Templates already up-to-date, nothing to add")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error auto-populating templates: {e}")
            # Don't raise - let the app continue without templates
