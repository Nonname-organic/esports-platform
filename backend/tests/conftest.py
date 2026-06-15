import asyncio
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.redis import RedisCache, get_redis
from app.main import app
from app.models.base import Base
from app.models.enums import UserRole
from app.models.user import User
from app.core.security import hash_password, create_access_token

# 既定はローカル。CI 等では TEST_DATABASE_URL で上書き可能（後方互換のため既定値は維持）。
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://esports_user:password@localhost:5432/esports_test",
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    class FakeRedisCache:
        async def get(self, key): return None
        async def set(self, key, value, ttl): pass
        async def delete(self, key): pass
        async def delete_pattern(self, pattern): return 0
        async def exists(self, key): return False
        async def acquire_lock(self, key, ttl=10): return True
        async def release_lock(self, key): pass
        async def publish(self, channel, message): pass
        async def increment(self, key, ttl=None): return 1

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: None

    from app.core.dependencies import get_cache
    app.dependency_overrides[get_cache] = lambda: FakeRedisCache()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        username="admin",
        hashed_password=hash_password("Admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(str(admin_user.id), {"role": UserRole.ADMIN.value})


@pytest_asyncio.fixture
async def organizer_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="organizer@test.com",
        username="organizer",
        hashed_password=hash_password("Organizer123"),
        role=UserRole.ORGANIZER,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
def organizer_token(organizer_user: User) -> str:
    return create_access_token(str(organizer_user.id), {"role": UserRole.ORGANIZER.value})


@pytest_asyncio.fixture
async def player_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(), email="player@test.com", username="player",
        hashed_password=hash_password("Player123"), role=UserRole.PLAYER, is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
def player_token(player_user: User) -> str:
    return create_access_token(str(player_user.id), {"role": UserRole.PLAYER.value})


@pytest_asyncio.fixture
async def second_player_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(), email="player2@test.com", username="player2",
        hashed_password=hash_password("Player123"), role=UserRole.PLAYER, is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
def second_player_token(second_player_user: User) -> str:
    return create_access_token(str(second_player_user.id), {"role": UserRole.PLAYER.value})


def auth_headers(token: str) -> dict:
    """Bearer ヘッダ生成ヘルパ。"""
    return {"Authorization": f"Bearer {token}"}
