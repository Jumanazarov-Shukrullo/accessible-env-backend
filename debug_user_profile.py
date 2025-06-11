#!/usr/bin/env python
"""Debug script to check user profile data."""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from app.db.session import get_db
from app.models.user_model import User, UserProfile, UserSecurity
from sqlalchemy.orm import joinedload

def check_user_profiles():
    """Check all users and their profile data."""
    db = get_db()  # Get the database session
    
    try:
        # Get all users with their profiles
        users = db.query(User).options(
            joinedload(User.profile),
            joinedload(User.security),
            joinedload(User.role)
        ).all()
        
        print(f"Found {len(users)} users:")
        print("-" * 80)
        
        for user in users:
            print(f"User: {user.username} ({user.email})")
            print(f"  ID: {user.user_id}")
            print(f"  Active: {user.is_active}")
            print(f"  Email Verified: {user.email_verified}")
            print(f"  Role ID: {user.role_id}")
            print(f"  Created: {user.created_at}")
            
            if user.profile:
                print(f"  Profile:")
                print(f"    First Name: {user.profile.first_name}")
                print(f"    Surname: {user.profile.surname}")
                print(f"    Middle Name: {user.profile.middle_name}")
                print(f"    Full Name: {user.profile.full_name}")
                print(f"    Phone: {user.profile.phone_number}")
                print(f"    Picture: {user.profile.profile_picture}")
                print(f"    Language: {user.profile.language_preference}")
                print(f"    Profile Created: {user.profile.created_at}")
            else:
                print(f"  Profile: None")
            
            if user.security:
                print(f"  Security:")
                print(f"    Last Login: {user.security.last_login_at}")
                print(f"    Failed Attempts: {user.security.failed_login_attempts}")
                print(f"    2FA Enabled: {user.security.two_factor_enabled}")
            else:
                print(f"  Security: None")
            
            print("-" * 80)
            
    finally:
        db.close()

if __name__ == "__main__":
    check_user_profiles() 