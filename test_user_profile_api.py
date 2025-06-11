#!/usr/bin/env python
"""Test script to check user profile API response."""

import os
import sys
import json
sys.path.append(os.path.dirname(__file__))

from app.db.session import get_db
from app.models.user_model import User
from app.services.user_service import UserService
from app.domain.unit_of_work import UnitOfWork
from app.core.security import security_manager

def test_user_profile_api():
    """Test the user profile API response."""
    db = get_db()
    uow = UnitOfWork(db)
    
    try:
        user_service = UserService(uow)
        
        # Get the Google OAuth user
        user = user_service.get_user_by_email("shukrullo.coder@gmail.com")
        if not user:
            print("User not found!")
            return
        
        print(f"Found user: {user.username} ({user.email})")
        
        # Test the get_user_response method (same as API endpoint)
        response = user_service.get_user_response(user)
        
        print("\n" + "="*80)
        print("API RESPONSE (get_user_response method):")
        print("="*80)
        print(json.dumps(response.model_dump(), indent=2, default=str))
        
        print("\n" + "="*80)
        print("PROFILE DATA SPECIFICALLY:")
        print("="*80)
        if response.profile:
            print(json.dumps(response.profile.model_dump(), indent=2, default=str))
        else:
            print("Profile is None!")
            
        print("\n" + "="*80)
        print("RAW USER OBJECT CHECK:")
        print("="*80)
        print(f"User has profile: {user.profile is not None}")
        if user.profile:
            print(f"Profile first_name: {user.profile.first_name}")
            print(f"Profile surname: {user.profile.surname}")
            print(f"Profile full_name: {user.profile.full_name}")
            print(f"Profile picture: {user.profile.profile_picture}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_user_profile_api() 