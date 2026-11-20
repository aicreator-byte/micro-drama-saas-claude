"""One-off cleanup: clear Google-account ciphertext that no longer
decrypts with the current Fernet key (see
app.services.google_account_service.cleanup_undecryptable_credentials).

Run from the backend directory (uses backend/.env for the key):

    cd backend && venv/bin/python scripts/cleanup_undecryptable_credentials.py

Only clears fields that FAIL to decrypt; good rows are untouched.
Prints how many fields were cleared per type. Safe to re-run.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker  # noqa: E402
from app.services.google_account_service import (  # noqa: E402
    cleanup_undecryptable_credentials,
)


async def main() -> None:
    async with async_session_maker() as db:
        cleared = await cleanup_undecryptable_credentials(db)
    total = sum(cleared.values())
    print(f"Cleared undecryptable fields: {cleared} (total {total})")


if __name__ == "__main__":
    asyncio.run(main())
