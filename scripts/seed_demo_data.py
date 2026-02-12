"""
Seed demo data for LeadOps Agent.

This script reads demo_leads.csv and populates the database with:
- Lead records from CSV
- Default ScoringConfig with initial weights
- Default admin User with API key

Usage:
    cd backend/
    python -m scripts.seed_demo_data
"""

import asyncio
import csv
import hashlib
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path if running from scripts directory
backend_dir = Path(__file__).parent.parent / "backend"
if backend_dir.exists():
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.orm import Base, Lead, ScoringConfig, User


async def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def seed_database():
    """Seed the database with demo data."""
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # 1. Create default admin user
        print("\n[1/3] Creating default admin user...")

        api_key_hash = await hash_api_key("dev-api-key-change-me")
        admin_user = User(
            email="admin@leadops.dev",
            name="Admin User",
            api_key_hash=api_key_hash,
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()
        print(f"Created user: {admin_user.email} (ID: {admin_user.id})")

        # 2. Create default scoring config
        print("\n[2/3] Creating default scoring config...")

        scoring_config = ScoringConfig(
            weights={
                "budget_weight": 0.3,
                "urgency_weight": 0.25,
                "company_size_weight": 0.2,
                "industry_weight": 0.15,
                "source_weight": 0.1,
                "budget_scores": {
                    "under_10k": 10, "10k-25k": 30, "25k-50k": 50,
                    "50k-100k": 75, "over_100k": 100
                },
                "urgency_scores": {"low": 20, "medium": 60, "high": 100},
                "company_size_scores": {
                    "1-10": 20, "11-50": 40, "51-200": 60, "201-500": 80,
                    "501-1000": 90, "1001-5000": 95, "5000+": 100
                },
                "industry_scores": {
                    "SaaS": 90, "Fintech": 85, "Healthcare": 80,
                    "Manufacturing": 70, "Retail": 65, "Education": 60, "Other": 50
                },
                "source_scores": {
                    "referral": 100, "partner": 90, "website": 80, "webinar": 75,
                    "conference": 70, "linkedin": 65, "google_ads": 60,
                    "trade_show": 55, "cold_email": 40, "other": 30
                },
            },
            thresholds={
                "hot_threshold": 75,
                "warm_threshold": 50,
                "cold_threshold": 25
            },
        )
        session.add(scoring_config)
        await session.flush()
        print(f"Created scoring config (ID: {scoring_config.id})")

        # 3. Load and create leads from CSV
        print("\n[3/3] Loading leads from CSV...")

        csv_path = Path(__file__).parent.parent / "data" / "demo_leads.csv"

        if not csv_path.exists():
            print(f"CSV file not found at {csv_path}")
            return

        leads_created = 0
        leads_skipped = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Skip CSV injection attempts (leading =, +, -, @)
                    if any(row.get('first_name', '').startswith(c) for c in ['=', '+', '-', '@']):
                        print(f"Skipping potential CSV injection: {row.get('email', 'unknown')}")
                        leads_skipped += 1
                        continue

                    # Skip if missing critical fields
                    if not row.get('email') or not row.get('first_name') or not row.get('last_name'):
                        print(f"Skipping lead with missing critical fields: {row}")
                        leads_skipped += 1
                        continue

                    # Create lead
                    lead = Lead(
                        first_name=row['first_name'][:100],
                        last_name=row['last_name'][:100],
                        email=row['email'][:255],
                        phone=row.get('phone', '')[:50] or None,
                        company_name=row.get('company_name', '')[:200] or 'Unknown',
                        job_title=row.get('job_title', '')[:100] or None,
                        industry=row.get('industry', '')[:100] or None,
                        company_size=row.get('company_size', '')[:50] or None,
                        country=row.get('country', '')[:100] or None,
                        source=row.get('source', '')[:100] or None,
                        budget_range=row.get('budget_range', '')[:50] or None,
                        pain_point=row.get('pain_point', '')[:500] or None,
                        urgency=row.get('urgency', '')[:20] or None,
                        lead_message=row.get('lead_message', '')[:2000] or None,
                        status='new',
                    )

                    session.add(lead)
                    leads_created += 1

                    # Batch commit every 50 leads for performance
                    if leads_created % 50 == 0:
                        await session.commit()
                        print(f"  ... {leads_created} leads created so far")

                except Exception as e:
                    print(f"Error creating lead from row {row}: {e}")
                    leads_skipped += 1
                    continue

        # Final commit for remaining leads
        await session.commit()

        print(f"\nSuccessfully created {leads_created} leads")
        if leads_skipped > 0:
            print(f"Skipped {leads_skipped} invalid/malicious leads")

    await engine.dispose()

    # Print summary
    print("\n" + "="*60)
    print("SEED SUMMARY")
    print("="*60)
    print(f"Admin User: admin@leadops.dev")
    print(f"  API Key: dev-api-key-change-me")
    print(f"\nScoring Config created with default weights/thresholds")
    print(f"\nLeads: {leads_created} created, {leads_skipped} skipped")
    print("="*60)
    print("\nDatabase seeding complete! You can now start the API server.")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(seed_database())
