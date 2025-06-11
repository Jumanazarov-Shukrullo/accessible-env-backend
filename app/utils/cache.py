import functools
import json
import logging
import uuid
import decimal
from typing import Callable, Any
from datetime import datetime, date

import redis
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.state import InstanceState

from app.core.config import settings

logger = logging.getLogger(__name__)

class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects, Decimal objects, and datetime objects by converting them to appropriate string formats."""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, InstanceState):
            return None  # Skip SQLAlchemy internal state objects
        return super().default(obj)

class Cache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._instance._client = redis.from_url(
                    settings.cache.redis_url, 
                    decode_responses=True,
                    socket_timeout=settings.cache.redis_socket_timeout,
                    socket_connect_timeout=settings.cache.redis_socket_connect_timeout,
                    retry_on_timeout=settings.cache.redis_retry_on_timeout
                )
                cls._instance._ttl = settings.cache.ttl_seconds
                logger.info(f"Redis cache initialized with URL: {settings.cache.redis_url}")
            except redis.RedisError as e:
                logger.warning(f"Failed to initialize Redis cache: {str(e)}. Caching will be disabled.")
                cls._instance._client = None
        return cls._instance

    def _serialize_value(self, value: Any) -> Any:
        """Recursively convert SQLAlchemy objects to dictionaries and prepare for JSON serialization."""
        # Handle None values
        if value is None:
            return None
            
        # Handle SQLAlchemy InstanceState
        if isinstance(value, InstanceState):
            return None
            
        # Handle UUID objects
        if isinstance(value, uuid.UUID):
            return str(value)
            
        # Handle Decimal objects
        if isinstance(value, decimal.Decimal):
            return float(value)
            
        # Handle datetime objects
        if isinstance(value, (datetime, date)):
            return value.isoformat()
            
        # Handle SQLAlchemy models
        if hasattr(value, "__table__"):
            # Convert SQLAlchemy model to dict
            obj_dict = {}
            for column in value.__table__.columns:
                obj_dict[column.name] = self._serialize_value(getattr(value, column.name))
            
            # Handle extra attributes that might need serialization
            for key, val in value.__dict__.items():
                if key != "_sa_instance_state" and not key.startswith("_") and key not in obj_dict:
                    obj_dict[key] = self._serialize_value(val)
            return obj_dict
        
        # Handle lists
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        
        # Handle dictionaries
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        
        # Return primitive types as is
        return value

    # ------------------------------------------------------------------
    def get(self, key: str):
        if self._client is None:
            return None
            
        try:
            val = self._client.get(key)
            if val:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(val)
            logger.debug(f"Cache miss for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    def set(self, key: str, value, ttl: int | None = None):
        if self._client is None:
            return
            
        try:
            # Serialize value before storing
            serialized_value = self._serialize_value(value)
            self._client.set(key, json.dumps(serialized_value, cls=UUIDEncoder), ex=ttl or self._ttl)
            logger.debug(f"Set cache for key: {key}, TTL: {ttl or self._ttl}s")
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")

    def invalidate(self, key_prefix: str):
        if self._client is None:
            return
            
        try:
            keys = list(self._client.scan_iter(f"{key_prefix}*"))
            if keys:
                self._client.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} keys with prefix: {key_prefix}")
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")

    # ------------------------------------------------------------------
    def cacheable(self, key_builder: Callable, ttl: int | None = None):
        """Decorator for caching service results."""

        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if self._client is None:
                    return fn(*args, **kwargs)
                    
                try:
                    key = key_builder(*args, **kwargs)
                    cached = self.get(key)
                    if cached is not None:
                        return cached
                    result = fn(*args, **kwargs)
                    self.set(key, result, ttl)
                    return result
                except Exception as e:
                    logger.error(f"Error in cache decorator: {str(e)}")
                    # Fallback to original function
                    return fn(*args, **kwargs)

            return wrapper

        return decorator


cache = Cache()
