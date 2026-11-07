"""Command-line runner to trigger background tasks manually in development."""
import asyncio
from app.core.database import async_session_factory
from app.core.logging import setup_logging
from app.worker.tasks import flag_stale_accounts


async def main() -> None:
    """Execute flag_stale_accounts manually."""
    setup_logging(debug=True)
    ctx = {"session_factory": async_session_factory}
    print("Triggering flag_stale_accounts task manually...")
    result = await flag_stale_accounts(ctx)
    print(f"Task completed successfully: {result}")


if __name__ == "__main__":
    asyncio.run(main())
