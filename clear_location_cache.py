#!/usr/bin/env python3
"""
Clear cache for specific location
"""
import sys
sys.path.insert(0, '.')

from app.utils.cache import cache

def main():
    location_id = '0fbaa716-bbcc-44b2-8c90-7e20eead6e7'
    
    # Clear all possible cache keys for this location
    cache_keys = [
        f"location:detail:{location_id}",
        f"location_details:{location_id}",
        f"locations_filter:*",  # This might contain the location
    ]
    
    print(f"🧹 Clearing cache for location {location_id}")
    
    for key in cache_keys:
        try:
            cache.invalidate(key)
            print(f"✅ Cleared cache key: {key}")
        except Exception as e:
            print(f"⚠️  Could not clear {key}: {e}")
    
    print("✅ Cache cleared! Try refreshing the page.")

if __name__ == "__main__":
    main() 