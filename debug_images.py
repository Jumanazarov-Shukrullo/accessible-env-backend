#!/usr/bin/env python3
"""
Debug script to check location images in the database
"""
import sys
sys.path.insert(0, '.')

from app.db.session import db_manager
from app.domain.unit_of_work import UnitOfWork
from app.models.location_images_model import LocationImage
from app.services.location_service import LocationService

def main():
    location_id = '0fbaa716-bbcc-44b2-8c90-7e20eead6e7'
    print(f"🔍 Debugging location images for: {location_id}")
    
    # Create database session and UoW
    db = db_manager.SessionLocal()
    uow = UnitOfWork(db)
    
    try:
        # Check 1: Direct database query for all images
        all_images = db.query(LocationImage).all()
        print(f"📊 Total images in database: {len(all_images)}")
        
        if all_images:
            print("📷 Sample images:")
            for img in all_images[:3]:
                print(f"  - Location: {img.location_id}, Image: {img.image_id}, URL: {img.image_url}")
        
        # Check 2: Images for specific location
        location_images = db.query(LocationImage).filter(
            LocationImage.location_id == location_id
        ).all()
        print(f"📷 Images for location {location_id}: {len(location_images)}")
        
        for img in location_images:
            print(f"  - Image ID: {img.image_id}, URL: {img.image_url}")
        
        # Check 3: Using location repository
        location = uow.locations.get_full(location_id)
        if location:
            print(f"✅ Repository found location: {location.location_name}")
            print(f"📷 Repository images: {len(location.images) if location.images else 0}")
            if location.images:
                for img in location.images:
                    print(f"  - Repo Image: {img.image_id}, URL: {img.image_url}")
        else:
            print("❌ Repository didn't find location")
        
        # Check 4: Using location service
        service = LocationService(uow)
        try:
            location_detail = service.get_location_detail(location_id)
            if location_detail:
                print(f"✅ Service found location: {location_detail.location_name}")
                print(f"📷 Service images: {len(location_detail.images)}")
                for i, img in enumerate(location_detail.images):
                    print(f"  - Service Image {i+1}: {img}")
            else:
                print("❌ Service returned None")
        except Exception as e:
            print(f"❌ Service error: {e}")
            import traceback
            traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main() 