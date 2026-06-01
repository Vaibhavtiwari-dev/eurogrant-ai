import os
import hashlib
import logging
from redis import Redis

logger = logging.getLogger(__name__)

class LockoutService:
    def __init__(self):
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
        try:
            self.redis = Redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("LockoutService initialized with Redis")
        except Exception as e:
            logger.warning("LockoutService: Redis unavailable (%s). Lockout disabled.", e)
            self.redis = None

    def _make_key(self, email):
        h = hashlib.sha256(email.lower().encode()).hexdigest()
        return "lockout:count:" + h, "lockout:locked:" + h

    def check_locked(self, email):
        if not self.redis:
            return False
        _, lock_key = self._make_key(email)
        return self.redis.exists(lock_key) > 0

    def record_failure(self, email, max_attempts=5, window_seconds=900, lock_duration=1800):
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

    def reset(self, email):
        if not self.redis:
            return
        count_key, lock_key = self._make_key(email)
        self.redis.delete(count_key, lock_key)

lockout_service = LockoutService()
