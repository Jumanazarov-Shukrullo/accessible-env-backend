#!/usr/bin/env python
"""Test script to verify the UUID fix."""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from app.db.session import get_db
from app.models.user_model import User
from app.services.user_service import UserService
from app.domain.unit_of_work import UnitOfWork

def test_fix():
    """Test the UUID fix."""
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
        print(f"User ID type: {type(user.user_id)}")
        
        # Test the get_user_response method
        print("Testing get_user_response method...")
        response = user_service.get_user_response(user)
        
        print("SUCCESS: get_user_response worked!")
        print(f"Response user_id: {response.user_id} (type: {type(response.user_id)})")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_fix() 