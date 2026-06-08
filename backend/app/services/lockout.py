import hashlib
import logging
import os

from redis import Redis

logger = logging.getLogger(__name__)


class LockoutService:
    def __init__(self) -> None:
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
        self._degraded: bool = False
        try:
            self.redis = Redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("LockoutService initialized with Redis")
        except Exception:
            # Fail-open: lockout is best-effort. If Redis is down we still let
            # users log in, but we mark the service degraded so /health and
            # monitoring can flag it. Do NOT silently disable the rest of the
            # auth path — an attacker DoSing Redis must not bypass rate limits
            # at the API layer (slowapi) without this being visible.
            logger.error(
                "LockoutService: Redis unavailable — account lockout disabled",
                exc_info=True,
            )
            self.redis = None
            self._degraded = True

    def is_degraded(self) -> bool:
        """True if Redis is unavailable and lockout enforcement is disabled."""
        return self._degraded

    def _make_key(self, email: str) -> tuple[str, str]:
        h = hashlib.sha256(email.lower().encode()).hexdigest()
        return "lockout:count:" + h, "lockout:locked:" + h

    def check_locked(self, email: str) -> bool:
        if not self.redis:
            return False
        _, lock_key = self._make_key(email)
        return self.redis.exists(lock_key) > 0

    def record_failure(
        self,
        email: str,
        max_attempts: int = 5,
        window_seconds: int = 900,
        lock_duration: int = 1800,
    ) -> bool:
        if not self.redis:
            return False
        count_key, lock_key = self._make_key(email)
        attempts = self.redis.incr(count_key)
        if attempts == 1:
            self.redis.expire(count_key, window_seconds)
        if attempts >= max_attempts:
            self.redis.setex(lock_key, lock_duration, "1")
            self.redis.delete(count_key)
            return True
        return False

    def reset(self, email: str) -> None:
        if not self.redis:
            return
        count_key, lock_key = self._make_key(email)
        self.redis.delete(count_key, lock_key)


lockout_service = LockoutService()
