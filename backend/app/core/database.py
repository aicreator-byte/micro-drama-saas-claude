"""Database connection and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import subprocess
import os


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def _run_migrations() -> None:
    """Run alembic migrations"""
    # Run alembic upgrade head from backend directory
    # __file__ is in backend/app/core/database.py, so backend_dir is 3 levels up
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Use python -m alembic to ensure correct environment
    import sys
    python_exe = sys.executable
    result = subprocess.run(
        [python_exe, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Check if this is the "can't locate revision" error for old DB with existing tables
        if "Can't locate revision identified by" in result.stderr:
            # The old revision (027a9ef8737e) doesn't exist in migration history
            # Directly update alembic_version table to current head
            import sqlite3
            from app.core.config import settings
            # Extract database path from URL
            db_url = settings.DATABASE_URL
            if db_url.startswith("sqlite+aiosqlite:///"):
                db_path = db_url.replace("sqlite+aiosqlite:///", "")
            elif db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")
            else:
                raise RuntimeError(f"Unsupported database URL: {db_url}")

            # Get current head revision
            head_result = subprocess.run(
                [python_exe, "-m", "alembic", "heads"],
                cwd=backend_dir,
                capture_output=True,
                text=True,
            )
            if head_result.returncode == 0:
                # Parse head revision from output (e.g., "96117fdda23d (head)")
                head_line = head_result.stdout.strip()
                if " (head)" in head_line:
                    head_revision = head_line.split(" (head)")[0].strip()
                    # Update alembic_version table directly
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT version_num FROM alembic_version")
                    current = cursor.fetchone()
                    if current and current[0] == "027a9ef8737e":
                        cursor.execute("UPDATE alembic_version SET version_num = ?", (head_revision,))
                        conn.commit()
                    conn.close()
                    # Now try upgrade again
                    result2 = subprocess.run(
                        [python_exe, "-m", "alembic", "upgrade", "head"],
                        cwd=backend_dir,
                        capture_output=True,
                        text=True,
                    )
                    if result2.returncode == 0:
                        return  # Successfully upgraded after manual stamp
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")


async def init_db() -> None:
    """Initialize database - run migrations"""
    # Run migrations in a thread to avoid blocking
    import asyncio
    await asyncio.to_thread(_run_migrations)


async def close_db() -> None:
    await engine.dispose()