#!/usr/bin/env python3
"""
Debug script to check user roles and fix access control issues
Uses the real database configuration from settings
"""
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.db.session import db_manager
from app.models.user_model import User
from app.models.role_model import Role
from app.core.constants import RoleID

def debug_user_roles():
    """Debug user roles and access control"""
    print("🔍 Debugging User Roles and Access Control")
    print(f"📊 Database URL: {settings.database.database_url}")
    print("-" * 60)
    
    session = db_manager.SessionLocal()
    
    try:
        # Check all users and their roles
        print("👥 Current Users and Roles:")
        users = session.query(User).all()
        
        for user in users:
            role_name = "Unknown"
            if user.role_id:
                role = session.query(Role).filter(Role.role_id == user.role_id).first()
                if role:
                    role_name = role.role_name
            
            print(f"  • User: {user.username}")
            print(f"    Email: {user.email}")
            print(f"    Role ID: {user.role_id}")
            print(f"    Role Name: {role_name}")
            print(f"    Active: {user.is_active}")
            print()
        
        # Check role constants vs database
        print("🔧 Role Constants vs Database:")
        print("Constants:")
        for role_enum in RoleID:
            print(f"  • {role_enum.name}: {role_enum.value}")
        
        print("\nDatabase Roles:")
        roles = session.query(Role).all()
        for role in roles:
            print(f"  • {role.role_name}: {role.role_id}")
        
        # Find superadmin users
        print("\n👑 Superadmin Users:")
        superadmin_users = session.query(User).filter(User.role_id == RoleID.SUPERADMIN.value).all()
        if superadmin_users:
            for user in superadmin_users:
                print(f"  • {user.username} ({user.email})")
        else:
            print("  ⚠️  No superadmin users found!")
        
        # Find admin users
        print("\n🛡️  Admin Users:")
        admin_users = session.query(User).filter(User.role_id == RoleID.ADMIN.value).all()
        if admin_users:
            for user in admin_users:
                print(f"  • {user.username} ({user.email})")
        else:
            print("  ⚠️  No admin users found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

def fix_rabbitmq_url():
    """Fix the RabbitMQ URL typo"""
    print("\n🐰 RabbitMQ Configuration:")
    print(f"Current URL: {settings.messaging.rabbitmq_url}")
    
    if "ampq://" in settings.messaging.rabbitmq_url:
        print("⚠️  Found typo in RabbitMQ URL: 'ampq' should be 'amqp'")
        print("This needs to be fixed in the environment configuration")
    else:
        print("✅ RabbitMQ URL looks correct")

if __name__ == "__main__":
    debug_user_roles()
    fix_rabbitmq_url()
    print("\n" + "="*60)
    print("🎯 Summary:")
    print("1. Check if your user has the correct role_id")
    print("2. Verify role constants match database values")
    print("3. Fix RabbitMQ URL if needed")
    print("4. Check access control logic in routers") 