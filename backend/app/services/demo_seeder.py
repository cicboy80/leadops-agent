"""
Auto-seed demo data on first startup when AUTO_SEED_DEMO=true and the DB is empty.

Seeds 6 curated leads from CSV, creates admin user + scoring config.
Leads are left unscored so employers can click "Process Unscored Leads"
and watch the LLM-powered pipeline run in real-time.
"""

import csv
import hashlib
import logging
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models.orm import Lead, ScoringConfig, User

logger = logging.getLogger("leadops.demo_seeder")

# In Docker: /app/data/demo_leads_curated.csv (WORKDIR /app, COPY data/ into ./data/)
# Locally: search relative to this file then fall back to cwd
_HERE = Path(__file__).parent.parent.parent  # backend/
CSV_PATH = (
    _HERE.parent / "data" / "demo_leads_curated.csv"  # project root (local dev)
    if (_HERE.parent / "data" / "demo_leads_curated.csv").exists()
    else _HERE / "data" / "demo_leads_curated.csv"  # Docker (/app/data/)
)


async def seed_and_process_if_empty() -> None:
    """Check if DB is empty; if so, seed demo data (leads left unscored)."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(func.count()).select_from(Lead))
            count = result.scalar_one()
            if count > 0:
                logger.info("Database already has %d leads — skipping demo seed", count)
                return

        logger.info("Empty database detected — seeding demo data...")
        lead_count = await _seed_data()
        logger.info(
            "Demo seeding complete — %d unscored leads ready for pipeline processing",
            lead_count,
        )

    except Exception:
        logger.exception("Demo seeder failed")


async def _seed_data() -> int:
    """Insert admin user, scoring config, and leads from curated CSV. Returns lead count."""
    async with async_session_factory() as session:
        # 1. Admin user
        api_key_hash = hashlib.sha256(b"dev-api-key-change-me").hexdigest()
        admin = User(
            email="admin@leadops.dev",
            name="Admin User",
            api_key_hash=api_key_hash,
            is_active=True,
        )
        session.add(admin)

        # 2. Scoring config — keys match frontend Settings page expectations
        config = ScoringConfig(
            weights={
                "urgency": 2.5,
                "budget": 3.0,
                "company_size": 2.0,
                "pain_point": 1.5,
                "job_title": 1.0,
                "industry": 1.5,
                "source": 1.0,
            },
            thresholds={
                "hot": 75,
                "warm": 50,
            },
        )
        session.add(config)

        # 3. Leads from CSV (left unscored for live pipeline demo)
        lead_count = 0
        if not CSV_PATH.exists():
            logger.error("Curated CSV not found at %s", CSV_PATH)
            await session.commit()
            return lead_count

        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("email") or not row.get("first_name"):
                    continue
                lead = Lead(
                    first_name=row["first_name"][:100],
                    last_name=row["last_name"][:100],
                    email=row["email"][:255],
                    phone=row.get("phone", "")[:50] or None,
                    company_name=row.get("company_name", "")[:200] or "Unknown",
                    job_title=row.get("job_title", "")[:100] or None,
                    industry=row.get("industry", "")[:100] or None,
                    company_size=row.get("company_size", "")[:50] or None,
                    country=row.get("country", "")[:100] or None,
                    source=row.get("source", "")[:100] or None,
                    budget_range=row.get("budget_range", "")[:50] or None,
                    pain_point=row.get("pain_point", "")[:500] or None,
                    urgency=row.get("urgency", "")[:20] or None,
                    lead_message=row.get("lead_message", "")[:2000] or None,
                    status="NEW",
                )
                session.add(lead)
                lead_count += 1

        await session.commit()
        logger.info("Inserted %d leads, admin user, and scoring config", lead_count)
        return lead_count
