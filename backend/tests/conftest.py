"""Test configuration and fixtures"""
import pytest
import os
import tempfile
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db, engine as app_engine
from app.models import User, Project, SeriesBible, Character, Location, Episode, Scene, SceneCharacter, Dialogue, Prompt, Asset, GoogleAccount, FlowBridge, StoryEngine, AppSettings, Shot, SceneEngine, OAuthState


# Set required environment variables for tests
os.environ["NVIDIA_API_KEY"] = "test-key-for-tests"

# Test database — a temp FILE, not :memory:.
#
# The async auto-generate job runs in a background task while the test
# polls GET from another session. SQLite :memory: uses a single shared
# connection (SingletonThreadPool), so two concurrent sessions corrupt
# each other's transaction state (steps stuck at RUNNING, job FAILED).
# A file DB gives each session its own pooled connection, like
# production (micro_drama.db), and concurrent sessions then see each
# other's commits correctly.
_fd, _test_db_path = tempfile.mkstemp(suffix=".db", prefix="micro_drama_test_")
os.close(_fd)
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_test_db_path}"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionMaker = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncSession:
    """Override database dependency for tests"""
    async with TestAsyncSessionMaker() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    """Remove the temp test database file at the end of the session."""
    yield
    try:
        os.unlink(_test_db_path)
    except OSError:
        pass


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Create tables before each test"""
    print("SETUP FIXTURE: Starting...")
    print("SETUP: Creating tables in test database...")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("SETUP: Tables created")
    yield
    print("SETUP: Dropping tables...")
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception as e:
        print(f"SETUP: Error dropping tables: {e}")
    print("SETUP: Tables dropped")
    print("SETUP FIXTURE: Done")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def async_client(setup_database):
    """Create async test client with overridden database"""
    print("CLIENT FIXTURE: Starting...")
    print("CLIENT: Overriding database dependency...")
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    print("CLIENT: Closing...")
    # Close client synchronously using new event loop
    import asyncio
    asyncio.run(client.aclose())
    app.dependency_overrides.clear()
    print("CLIENT: Done")
    print("CLIENT FIXTURE: Done")