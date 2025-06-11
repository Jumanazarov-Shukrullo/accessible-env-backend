#!/usr/bin/env python
"""Test script to verify the locations API returns correct paginated format."""

import requests
import json

def test_locations_api():
    """Test the locations API endpoint."""
    try:
        # Test the main locations endpoint
        response = requests.get('http://localhost:8000/api/v1/locations/')
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Locations API working!")
            print(f"Response keys: {list(data.keys())}")
            print(f"Total locations: {data.get('total', 'N/A')}")
            print(f"Items count: {len(data.get('items', []))}")
            print(f"Page: {data.get('page', 'N/A')}")
            print(f"Size: {data.get('size', 'N/A')}")
            
            # Show first location if available
            items = data.get('items', [])
            if items:
                print(f"\nFirst location: {items[0].get('location_name', 'No name')}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_locations_api() 