#!/usr/bin/env python3
"""
Simple script to clear the assessment cache
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.cache import cache

def clear_assessment_cache():
    """Clear all assessment-related cache entries"""
    try:
        # Clear cache for set_id=1 (the one causing issues)
        cache.invalidate("assessment_sets:1:criteria")
        print("✅ Cleared cache for assessment_sets:1:criteria")
        
        # Clear other related cache entries
        cache.invalidate("assessment_sets:list")
        cache.invalidate("assessment_sets:1")
        cache.invalidate("criteria:list")
        print("✅ Cleared all assessment-related cache entries")
        
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")

if __name__ == "__main__":
    clear_assessment_cache() 