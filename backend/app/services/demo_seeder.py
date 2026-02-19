"""
Per-session demo data seeding when AUTO_SEED_DEMO=true.

Each visitor gets their own set of 6 unscored leads tagged with a unique
demo_session_id. Old sessions (>24h) are cleaned up on startup.
"""

import asyncio
import csv
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.orm import (
    ActivityLog,
    EmailDraft,
    Feedback,
    Lead,
    LeadOutcomeStage,
    Notification,
    PipelineRun,
    ReplyClassificationRecord,
    ScoringConfig,
    Trace,
    User,
)

logger = logging.getLogger("leadops.demo_seeder")

# In Docker: /app/data/demo_leads_curated.csv (WORKDIR /app, COPY data/ into ./data/)
# Locally: search relative to this file then fall back to cwd
_HERE = Path(__file__).parent.parent.parent  # backend/
CSV_PATH = (
    _HERE.parent / "data" / "demo_leads_curated.csv"  # project root (local dev)
    if (_HERE.parent / "data" / "demo_leads_curated.csv").exists()
    else _HERE / "data" / "demo_leads_curated.csv"  # Docker (/app/data/)
)

# In-memory set of session IDs that have been seeded (avoids DB round-trip per request)
_seeded_sessions: set[str] = set()
# Per-session locks to prevent concurrent double-seeding
_seed_locks: dict[str, asyncio.Lock] = {}


async def cleanup_old_sessions() -> None:
    """Delete demo leads (+ children) older than 24 hours. Runs on startup."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        async with async_session_factory() as session:
            # Find old demo leads
            old_lead_ids_stmt = (
                select(Lead.id)
                .where(Lead.demo_session_id.is_not(None))
                .where(Lead.created_at < cutoff)
            )
            result = await session.execute(old_lead_ids_stmt)
            old_lead_ids = [row[0] for row in result.all()]

            if not old_lead_ids:
                logger.info("No stale demo sessions to clean up")
                return

            # Delete children first (FK safety)
            for child_model in (
                Notification, ReplyClassificationRecord, LeadOutcomeStage,
                PipelineRun, Trace, Feedback, EmailDraft, ActivityLog,
            ):
                await session.execute(
                    delete(child_model).where(child_model.lead_id.in_(old_lead_ids))
                )

            # Delete the leads themselves
            await session.execute(
                delete(Lead).where(Lead.id.in_(old_lead_ids))
            )
            await session.commit()
            logger.info("Cleaned up %d stale demo leads", len(old_lead_ids))
    except Exception:
        logger.exception("Demo session cleanup failed")


async def seed_for_session(session_id: str, db: AsyncSession) -> None:
    """Insert 6 curated leads tagged with demo_session_id for this visitor."""
    if session_id in _seeded_sessions:
        return

    # Per-session lock prevents concurrent requests from double-seeding
    if session_id not in _seed_locks:
        _seed_locks[session_id] = asyncio.Lock()
    async with _seed_locks[session_id]:
        # Re-check after acquiring lock (another request may have seeded)
        if session_id in _seeded_sessions:
            return

        # DB fallback: check if leads already exist for this session
        result = await db.execute(
            select(func.count()).select_from(Lead).where(Lead.demo_session_id == session_id)
        )
        if result.scalar_one() > 0:
            _seeded_sessions.add(session_id)
            return

        if not CSV_PATH.exists():
            logger.error("Curated CSV not found at %s", CSV_PATH)
            return

        lead_count = 0
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
                    demo_session_id=session_id,
                )
                db.add(lead)
                lead_count += 1

        await db.flush()
        _seeded_sessions.add(session_id)
        logger.info("Seeded %d leads for demo session %s", lead_count, session_id[:8])


async def ensure_admin_and_config() -> None:
    """Create admin user and scoring config if they don't already exist."""
    async with async_session_factory() as session:
        # Admin user — skip if exists
        result = await session.execute(
            select(func.count()).select_from(User).where(User.email == "admin@leadops.dev")
        )
        if result.scalar_one() == 0:
            api_key_hash = hashlib.sha256(b"dev-api-key-change-me").hexdigest()
            session.add(User(
                email="admin@leadops.dev",
                name="Admin User",
                api_key_hash=api_key_hash,
                is_active=True,
            ))

        # Scoring config — skip if exists
        result = await session.execute(
            select(func.count()).select_from(ScoringConfig)
        )
        if result.scalar_one() == 0:
            session.add(ScoringConfig(
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
            ))

        await session.commit()
