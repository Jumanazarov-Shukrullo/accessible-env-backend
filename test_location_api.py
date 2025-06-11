#!/usr/bin/env python
"""Test script to verify the location API returns correct normalized data structure."""

import requests
import json

def test_single_location():
    """Test getting a single location to verify all fields are present."""
    try:
        # First get the list to find a location ID
        response = requests.get('http://localhost:8000/api/v1/locations/')
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            if items:
                location_id = items[0]['location_id']
                print(f"Testing location ID: {location_id}")
                
                # Now get the specific location
                location_response = requests.get(f'http://localhost:8000/api/v1/locations/{location_id}')
                
                if location_response.status_code == 200:
                    location_data = location_response.json()
                    print("✅ Single location API working!")
                    print("Location fields:")
                    for key, value in location_data.items():
                        if key == 'images' and isinstance(value, list):
                            print(f"  {key}: {len(value)} images")
                        elif key == 'details' and value:
                            print(f"  {key}: {type(value).__name__}")
                            for detail_key, detail_value in value.items():
                                print(f"    {detail_key}: {detail_value}")
                        elif key == 'stats' and value:
                            print(f"  {key}: {type(value).__name__}")
                            for stat_key, stat_value in value.items():
                                print(f"    {stat_key}: {stat_value}")
                        else:
                            print(f"  {key}: {value}")
                            
                    # Check if flattened fields are present
                    flattened_fields = ['contact_info', 'website_url', 'description', 'operating_hours', 'accessibility_score']
                    print("\nFlattened fields check:")
                    for field in flattened_fields:
                        if field in location_data:
                            print(f"  ✅ {field}: {location_data[field]}")
                        else:
                            print(f"  ❌ {field}: MISSING")
                            
                else:
                    print(f"❌ Single location API Error: {location_response.status_code}")
                    print(location_response.text)
            else:
                print("❌ No locations found in list")
        else:
            print(f"❌ List API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_single_location() 