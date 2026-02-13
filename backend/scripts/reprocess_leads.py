"""
Re-process all scored leads to populate score_breakdown in enrichment_data.

Usage:
    cd backend && python3 -m scripts.reprocess_leads
"""

import asyncio
import sys
import uuid

from sqlalchemy import select

# Ensure app modules are importable
sys.path.insert(0, ".")

from app.core.database import async_session_factory
from app.models.orm import Lead
from app.services.pipeline_service import PipelineService


async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(Lead.id).where(Lead.score_value.isnot(None))
        )
        lead_ids: list[uuid.UUID] = [row[0] for row in result.all()]

    print(f"Found {len(lead_ids)} scored leads to re-process")

    success = 0
    failed = 0

    for i, lead_id in enumerate(lead_ids, 1):
        async with async_session_factory() as session:
            try:
                svc = PipelineService(session)
                await svc.run_pipeline(lead_id)
                await session.commit()
                success += 1
                if i % 10 == 0:
                    print(f"  [{i}/{len(lead_ids)}] processed...")
            except Exception as exc:
                failed += 1
                print(f"  FAILED lead {lead_id}: {exc}")

    print(f"\nDone: {success} succeeded, {failed} failed out of {len(lead_ids)} leads")


if __name__ == "__main__":
    asyncio.run(main())
