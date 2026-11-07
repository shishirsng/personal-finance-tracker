"""ARQ Background tasks."""
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.transaction import Transaction

logger = get_logger("app.worker.tasks")


async def flag_stale_accounts(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Daily background job: Flags accounts with no transactions within the past 90 days.
    Updates Account.is_stale = True, and records an AuditLog event.
    """
    session_factory = ctx["session_factory"]
    threshold_date = datetime.now(timezone.utc) - timedelta(days=90)

    async with session_factory() as session:
        session: AsyncSession
        # Accounts with no activity in 90 days or no transactions at all and created > 90 days ago
        stmt = (
            select(Account)
            .where(
                Account.is_stale.is_(False),
                (
                    (Account.last_activity_at < threshold_date)
                    | (
                        Account.last_activity_at.is_(None)
                        & (Account.created_at < threshold_date)
                    )
                ),
            )
        )
        result = await session.execute(stmt)
        candidate_accounts = result.scalars().all()

        flagged_ids: list[str] = []
        for account in candidate_accounts:
            # Confirm no transactions in past 90 days
            tx_stmt = (
                select(Transaction.id)
                .where(
                    Transaction.account_id == account.id,
                    Transaction.occurred_at >= threshold_date,
                )
                .limit(1)
            )
            tx_res = await session.execute(tx_stmt)
            if tx_res.scalar_one_or_none() is None:
                account.is_stale = True
                flagged_ids.append(str(account.id))

        if flagged_ids:
            import uuid
            audit_entry = AuditLog(
                id=uuid.uuid4(),
                event_type="STALE_ACCOUNTS_FLAGGED",
                payload={
                    "flagged_count": len(flagged_ids),
                    "account_ids": flagged_ids,
                    "threshold_date": threshold_date.isoformat(),
                },
            )
            session.add(audit_entry)
            await session.commit()

        logger.info(
            "flag_stale_accounts_completed",
            stale_count=len(flagged_ids),
            accounts=flagged_ids,
        )
        return {"flagged_count": len(flagged_ids), "flagged_ids": flagged_ids}
