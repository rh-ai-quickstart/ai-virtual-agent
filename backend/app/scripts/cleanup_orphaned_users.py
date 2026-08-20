"""
CronJob script: delete orphaned user rows from the DB.

A user is orphaned when they exist in the app's ``users`` table but no
longer exist in Keycloak (e.g. deleted via the Keycloak admin console).

Run via: python -m backend.app.scripts.cleanup_orphaned_users
"""

import asyncio
import logging
import sys

import httpx
from sqlalchemy import select, text

from backend.app.core.oauth import (
    KEYCLOAK_REALM,
    KEYCLOAK_SERVER_URL_INTERNAL,
    get_keycloak_admin_token,
)
from backend.app.database import AsyncSessionLocal
from backend.app.models.user import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def fetch_all_keycloak_user_ids() -> set[str]:
    """Paginate through the Keycloak Admin API to collect every user ID."""
    token = await get_keycloak_admin_token()
    url = f"{KEYCLOAK_SERVER_URL_INTERNAL}/admin/realms/{KEYCLOAK_REALM}/users"
    all_ids: set[str] = set()
    first = 0
    page_size = 500

    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                url,
                params={"first": first, "max": page_size},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            users = resp.json()
            if not users:
                break
            all_ids.update(u["id"] for u in users)
            if len(users) < page_size:
                break
            first += page_size

    return all_ids


async def main() -> None:
    logger.info("Starting orphaned-user cleanup")

    try:
        kc_ids = await fetch_all_keycloak_user_ids()
    except Exception as exc:
        logger.error("Failed to fetch users from Keycloak — aborting: %s", exc)
        sys.exit(1)

    logger.info("Keycloak users: %d", len(kc_ids))

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(User.keycloak_id))).all()
        db_ids = {str(row[0]) for row in rows}

    logger.info("DB users: %d", len(db_ids))

    orphan_ids = db_ids - kc_ids
    if not orphan_ids:
        logger.info("No orphaned users found — nothing to do")
        return

    if db_ids and len(orphan_ids) > len(db_ids) / 2:
        logger.error(
            "Orphan count (%d) exceeds 50%% of DB users (%d) — aborting as a "
            "safety measure (Keycloak may be returning incomplete data)",
            len(orphan_ids),
            len(db_ids),
        )
        sys.exit(1)

    logger.info("Orphaned users to remove: %d", len(orphan_ids))

    total_guardrails = 0
    total_kb = 0
    deleted = 0

    for uid in orphan_ids:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    r1 = await session.execute(
                        text(
                            "UPDATE guardrails SET created_by = NULL "
                            "WHERE created_by = :uid"
                        ),
                        {"uid": uid},
                    )
                    r2 = await session.execute(
                        text(
                            "UPDATE knowledge_bases SET created_by = NULL "
                            "WHERE created_by = :uid"
                        ),
                        {"uid": uid},
                    )
                    await session.execute(
                        text("DELETE FROM users WHERE keycloak_id = :uid"),
                        {"uid": uid},
                    )
                total_guardrails += r1.rowcount
                total_kb += r2.rowcount
                deleted += 1
                logger.info("Deleted orphaned user %s", uid)
        except Exception as exc:
            logger.error("Failed to delete user %s: %s", uid, exc)

    logger.info(
        "Cleanup complete: deleted %d/%d orphaned users, "
        "nullified %d guardrails and %d knowledge_bases references",
        deleted,
        len(orphan_ids),
        total_guardrails,
        total_kb,
    )


if __name__ == "__main__":
    asyncio.run(main())
