"""Tests for ARQ background worker tasks."""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.user import User
from app.worker.tasks import flag_stale_accounts


@pytest.mark.asyncio
async def test_flag_stale_accounts_job(db_session: AsyncSession, user_a: User):
    # 1. Create stale account (activity > 100 days ago)
    stale_date = datetime.now(timezone.utc) - timedelta(days=100)
    stale_acc = Account(
        id=uuid.uuid4(),
        user_id=user_a.id,
        name="Old Dormant Account",
        type="savings",
        currency="USD",
        is_stale=False,
        last_activity_at=stale_date,
        created_at=stale_date,
    )

    # 2. Create active account (activity today)
    active_acc = Account(
        id=uuid.uuid4(),
        user_id=user_a.id,
        name="Fresh Active Account",
        type="checking",
        currency="USD",
        is_stale=False,
        last_activity_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([stale_acc, active_acc])
    await db_session.commit()

    # Sessionmaker factory wrapper for worker context
    engine = db_session.bind
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    ctx = {"session_factory": session_factory}

    # 3. Execute worker task
    result = await flag_stale_accounts(ctx)
    assert result["flagged_count"] >= 1
    assert str(stale_acc.id) in result["flagged_ids"]

    # 4. Verify account state in DB
    await db_session.refresh(stale_acc)
    await db_session.refresh(active_acc)
    assert stale_acc.is_stale is True
    assert active_acc.is_stale is False

    # 5. Verify audit log entry
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "STALE_ACCOUNTS_FLAGGED")
    )
    log = audit_res.scalar_one_or_none()
    assert log is not None
    assert log.payload["flagged_count"] >= 1
