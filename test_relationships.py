#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/home/hettiera/diplom/backend')

from app.models.user_model import User
from app.models.role_model import Role
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

def test_relationships():
    # Test database connection and relationships
    engine = create_engine('postgresql://postgres:LdQTEzMqnqNIEQwVrOWQUlxfQBpXTbXX@ballast.proxy.rlwy.net:41773/railway')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        print("Testing database connection...")
        
        # Test simple user query
        user_count = session.query(User).count()
        print(f'Users found: {user_count}')
        
        # Test role query
        role_count = session.query(Role).count()
        print(f'Roles found: {role_count}')
        
        # Test relationship
        user = session.query(User).first()
        if user:
            print(f'First user: {user.username}, role_id: {user.role_id}')
            if user.role:
                print(f'User role: {user.role.role_name}')
        
        print("Database relationships test completed successfully!")
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_relationships() 