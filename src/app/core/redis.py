"""Redis connection and utilities."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis
from redis import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with connection management."""

    def __init__(self) -> None:
        self._client: Redis | None = None

    def connect(self) -> Redis:
        """Create and return a Redis connection."""
        if self._client is None:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return self._client

    def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    @property
    def client(self) -> Redis:
        """Get the Redis client, connecting if necessary."""
        if self._client is None:
            return self.connect()
        return self._client

    def is_connected(self) -> bool:
        """Check if Redis is connected and responsive."""
        try:
            if self._client:
                self._client.ping()
                return True
        except redis.ConnectionError:
            pass
        return False

    def health_check(self) -> dict:
        """Perform a health check on Redis connection."""
        try:
            if self._client:
                self._client.ping()
                info = self._client.info("server")
                return {
                    "status": "healthy",
                    "version": info.get("redis_version", "unknown"),
                    "connected_clients": self._client.info("clients").get(
                        "connected_clients", 0
                    ),
                }
        except redis.ConnectionError as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
        return {"status": "not_connected"}


# Global Redis client instance
redis_client = RedisClient()


def get_redis() -> Redis:
    """Dependency to get Redis client."""
    return redis_client.client


@asynccontextmanager
async def redis_lifespan() -> AsyncGenerator[None, None]:
    """Async context manager for Redis connection lifecycle."""
    redis_client.connect()
    try:
        yield
    finally:
        redis_client.disconnect()
