"""
Simple Redis-backed counters for tracking usage metrics.
Provides get/increment/reset operations for production observability.
"""

import os
import redis
import logging
from typing import Dict, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class MetricsManager:
    """
    Manages application metrics using Redis as the backend.
    Counters persist across restarts and can be queried from the admin panel.
    """
    
    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None):
        """
        Initialize Redis connection.
        
        Args:
            redis_host: Redis hostname (defaults to env REDIS_HOST or 'redis')
            redis_port: Redis port (defaults to env REDIS_PORT or 6379)
        """
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(redis_port or os.getenv('REDIS_PORT', 6379))
        
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Metrics will not persist.")
            self.redis_client = None
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter and return the new value."""
        if not self.redis_client:
            return None
        try:
            new_value = self.redis_client.incr(key, amount)
            logger.debug(f"Incremented {key} to {new_value}")
            return new_value
        except Exception as e:
            logger.error(f"Failed to increment {key}: {e}")
            return None
    
    def get(self, key: str) -> int:
        """Get the current value of a counter."""
        if not self.redis_client:
            return 0
        try:
            value = self.redis_client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Failed to get {key}: {e}")
            return 0
    
    def set(self, key: str, value: int) -> bool:
        """Set a counter to a specific value."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set {key}: {e}")
            return False
    
    def reset(self, key: str) -> bool:
        """Reset a counter to 0."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset {key}: {e}")
            return False
    
    def reset_all(self) -> bool:
        """Reset all app metrics (use with caution)."""
        if not self.redis_client:
            return False
        try:
            keys = self.redis_client.keys('app:*')
            if keys:
                self.redis_client.delete(*keys)
            logger.info(f"Reset {len(keys)} metric keys")
            return True
        except Exception as e:
            logger.error(f"Failed to reset all metrics: {e}")
            return False
    
    def get_all(self) -> Dict[str, int]:
        """Get all application metrics."""
        if not self.redis_client:
            return {}
        try:
            keys = self.redis_client.keys('app:*')
            result = {}
            for key in keys:
                value = self.redis_client.get(key)
                result[key] = int(value) if value else 0
            return result
        except Exception as e:
            logger.error(f"Failed to get all metrics: {e}")
            return {}
    
    def record_event(self, event_type: str) -> None:
        """
        Record a timestamped event for audit trails.
        Stores as a Redis list with latest events.
        """
        if not self.redis_client:
            return
        try:
            timestamp = datetime.utcnow().isoformat()
            self.redis_client.lpush(f"app:events:{event_type}", f"{timestamp}")
            # Keep only the last 100 events per type
            self.redis_client.ltrim(f"app:events:{event_type}", 0, 99)
        except Exception as e:
            logger.error(f"Failed to record event {event_type}: {e}")


# Global instance
_metrics_manager: Optional[MetricsManager] = None


def get_metrics() -> MetricsManager:
    """Get or initialize the global metrics manager."""
    global _metrics_manager
    if _metrics_manager is None:
        _metrics_manager = MetricsManager()
    return _metrics_manager


# Counter key constants
COUNTER_BOT_STARTS = "app:bot:starts:total"
COUNTER_REGISTRATIONS_SUCCESS = "app:registrations:success:total"
COUNTER_REGISTRATIONS_FAILED = "app:registrations:failed:total"
COUNTER_REMINDERS_SENT = "app:reminders:sent:total"
COUNTER_REMINDERS_FAILED = "app:reminders:failed:total"
COUNTER_ADMIN_STARTS = "app:admin:starts:total"
