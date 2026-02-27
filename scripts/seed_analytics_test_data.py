#!/usr/bin/env python3
"""
Seed test data for analytics verification.

Usage:
    docker compose exec api python scripts/seed_analytics_test_data.py
"""

import asyncio
import hashlib
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.models.click_event import ClickEvent
from app.db.models.content_map import ContentMap
from app.db.models.inbound_event import InboundEvent


async def seed_data(session: AsyncSession) -> dict:
    """Seed test analytics data for existing campaigns."""
    
    # Get all active campaigns
    campaigns_q = select(ContentMap).where(ContentMap.is_active.is_(True))
    campaigns_result = await session.execute(campaigns_q)
    campaigns = list(campaigns_result.scalars().all())
    
    if not campaigns:
        print("No active campaigns found. Please create campaigns first.")
        return {"error": "no_campaigns"}
    
    print(f"Found {len(campaigns)} active campaigns:")
    for c in campaigns:
        print(f"  - {c.content_ref} (slug={c.slug}, start_param={c.start_param})")
    
    stats = {
        "inbound_events_created": 0,
        "click_events_created": 0,
    }
    
    now = datetime.now(UTC)
    
    # Spread data over 10 days to test 24h vs 7d properly
    DAYS_TO_SEED = 10
    HOURS_TO_SEED = DAYS_TO_SEED * 24
    
    for campaign in campaigns:
        # Create InboundEvent records (resolve requests)
        # Simulate 10 days of traffic with varying patterns
        for hours_ago in range(HOURS_TO_SEED):
            event_time = now - timedelta(hours=hours_ago)
            
            # Traffic pattern: more recent = more traffic
            # Day 0-1: 3-8 resolves/hour
            # Day 1-3: 2-5 resolves/hour
            # Day 3-7: 1-3 resolves/hour
            # Day 7+: 0-2 resolves/hour
            if hours_ago < 24:
                num_resolves = random.randint(3, 8)
            elif hours_ago < 72:
                num_resolves = random.randint(2, 5)
            elif hours_ago < 168:
                num_resolves = random.randint(1, 3)
            else:
                num_resolves = random.randint(0, 2)
            
            for _ in range(num_resolves):
                # Randomize result: 70% hit, 20% fallback_payload, 10% fallback_catalog
                result_roll = random.random()
                if result_roll < 0.7:
                    result = "hit"
                elif result_roll < 0.9:
                    result = "fallback_payload"
                else:
                    result = "fallback_catalog"
                
                # Generate unique payload hash
                payload_hash = hashlib.sha256(
                    f"{campaign.content_ref}:{uuid.uuid4()}".encode()
                ).hexdigest()
                
                inbound = InboundEvent(
                    channel=campaign.channel,
                    payload_hash=payload_hash,
                    content_ref=campaign.content_ref,
                    mc_contact_id=f"test_contact_{random.randint(1000, 9999)}",
                    mc_flow_id=f"test_flow_{random.randint(1, 10)}",
                    text_preview="test resolve request",
                    result=result,
                    resolved_slug=campaign.slug,
                    resolved_start_param=campaign.start_param,
                    latency_ms=random.randint(10, 100),
                    request_id=f"test_{uuid.uuid4().hex[:8]}",
                    payload_min={},
                    created_at=event_time - timedelta(minutes=random.randint(0, 59)),
                )
                session.add(inbound)
                stats["inbound_events_created"] += 1
        
        # Create ClickEvent records (shortlink clicks)
        # Clicks are typically fewer than resolves (CTR ~50-70%)
        for hours_ago in range(HOURS_TO_SEED):
            event_time = now - timedelta(hours=hours_ago)
            
            # Clicks follow similar pattern but fewer
            if hours_ago < 24:
                num_clicks = random.randint(2, 5)
            elif hours_ago < 72:
                num_clicks = random.randint(1, 3)
            elif hours_ago < 168:
                num_clicks = random.randint(0, 2)
            else:
                num_clicks = random.randint(0, 1)
            
            for _ in range(num_clicks):
                # 5% chance of miss (bad slug, etc.)
                is_miss = random.random() < 0.05
                
                click = ClickEvent(
                    content_map_id=campaign.id,
                    slug=campaign.slug,
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Test",
                    ip_hash=None,  # No IP logging for test
                    referer="https://instagram.com/test",
                    meta={"miss": True} if is_miss else {},
                    created_at=event_time - timedelta(minutes=random.randint(0, 59)),
                )
                session.add(click)
                stats["click_events_created"] += 1
    
    await session.commit()
    return stats


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("=" * 60)
    print("SocialBridge Analytics Test Data Seeder")
    print("=" * 60)
    
    async with async_session() as session:
        result = await seed_data(session)
    
    await engine.dispose()
    
    if "error" not in result:
        print("\nSeeding complete!")
        print(f"  InboundEvents created: {result['inbound_events_created']}")
        print(f"  ClickEvents created: {result['click_events_created']}")
        print("\nYou can now test analytics in the Wizard bot!")
    else:
        print(f"\nSeeding failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
