import time
import json
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cached response entry."""
    response: str
    extracted_data: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > ttl_seconds
    
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()

class ResponseCache:
    """Advanced caching system for GPT responses and common queries."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.intent_cache: Dict[str, str] = {}  # Intent to response mapping
        self.similarity_threshold = 0.8
        
    def _generate_key(self, user_input: str, context: Optional[Dict] = None) -> str:
        """Generate cache key from user input and context."""
        # Normalize input
        normalized_input = self._normalize_input(user_input)
        
        # Create context signature
        context_sig = ""
        if context:
            context_sig = str(hash(frozenset(context.items())))
        
        # Generate hash key
        key_data = f"{normalized_input}:{context_sig}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _normalize_input(self, text: str) -> str:
        """Normalize input text for better caching."""
        # Convert to lowercase and remove extra whitespace
        text = ' '.join(text.lower().split())
        
        # Remove punctuation for intent matching
        import string
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def get(self, user_input: str, context: Optional[Dict] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Get cached response if available."""
        key = self._generate_key(user_input, context)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Check if expired
            if entry.is_expired(self.default_ttl):
                del self.cache[key]
                logger.debug(f"Cache entry expired: {key}")
                return None
            
            # Update access statistics
            entry.update_access()
            
            logger.debug(f"Cache hit for key: {key}")
            return entry.response, entry.extracted_data
        
        # Try intent-based caching
        normalized_input = self._normalize_input(user_input)
        for cached_input, response_key in self.intent_cache.items():
            similarity = self._calculate_similarity(normalized_input, cached_input)
            
            if similarity >= self.similarity_threshold and response_key in self.cache:
                entry = self.cache[response_key]
                if not entry.is_expired(self.default_ttl):
                    entry.update_access()
                    logger.debug(f"Intent cache hit: {similarity:.2f}")
                    return entry.response, entry.extracted_data
        
        return None
    
    def set(self, user_input: str, response: str, extracted_data: Dict[str, Any], 
            context: Optional[Dict] = None, ttl: Optional[int] = None) -> None:
        """Store response in cache."""
        key = self._generate_key(user_input, context)
        ttl = ttl or self.default_ttl
        
        # Clean up expired entries
        self._cleanup_expired()
        
        # Evict least recently used if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Store in cache
        entry = CacheEntry(
            response=response,
            extracted_data=extracted_data,
            timestamp=time.time()
        )
        self.cache[key] = entry
        
        # Store in intent cache for similarity matching
        normalized_input = self._normalize_input(user_input)
        self.intent_cache[normalized_input] = key
        
        logger.debug(f"Cache stored for key: {key}")
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry.timestamp > self.default_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
            # Also remove from intent cache
            self.intent_cache = {k: v for k, v in self.intent_cache.items() if v != key}
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Find entry with lowest access count and oldest last accessed time
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k].access_count, self.cache[k].last_accessed)
        )
        
        del self.cache[lru_key]
        self.intent_cache = {k: v for k, v in self.intent_cache.items() if v != lru_key}
        
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        
        # Calculate hit rate (approximate)
        current_time = time.time()
        recent_entries = [
            entry for entry in self.cache.values()
            if current_time - entry.timestamp < 3600  # Last hour
        ]
        recent_accesses = sum(entry.access_count for entry in recent_entries)
        
        return {
            "total_entries": total_entries,
            "max_size": self.max_size,
            "total_accesses": total_accesses,
            "recent_accesses": recent_accesses,
            "hit_rate_estimate": recent_accesses / max(total_entries, 1),
            "intent_cache_size": len(self.intent_cache),
            "memory_usage_mb": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        import sys
        total_size = 0
        
        for key, entry in self.cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(entry.response)
            total_size += sys.getsizeof(entry.extracted_data)
        
        for key, value in self.intent_cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(value)
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.intent_cache.clear()
        logger.info("Cache cleared")
    
    def warm_cache(self, common_queries: Dict[str, Tuple[str, Dict]]):
        """Warm cache with common queries."""
        for query, (response, data) in common_queries.items():
            self.set(query, response, data)
        logger.info(f"Cache warmed with {len(common_queries)} entries")

# Global cache instance
response_cache = ResponseCache()

# Common real estate queries for cache warming
COMMON_QUERIES = {
    "are you looking to buy or rent": (
        "Great! Are you looking to buy or rent a property?",
        {"intent": "property_type"}
    ),
    "which area are you interested in": (
        "Which area are you interested in?",
        {"intent": "location"}
    ),
    "what type of property": (
        "What type of property are you looking for - villa, apartment, or penthouse?",
        {"intent": "property_preference"}
    ),
    "what's your budget range": (
        "What's your budget range for this property?",
        {"intent": "budget"}
    ),
    "when would you like to view": (
        "When would you like to schedule a viewing?",
        {"intent": "schedule"}
    ),
    "may i have your name": (
        "May I have your name, please?",
        {"intent": "name_collection"}
    ),
    "and your email address": (
        "And your email address?",
        {"intent": "email_collection"}
    )
}

# Initialize cache with common queries
response_cache.warm_cache(COMMON_QUERIES)