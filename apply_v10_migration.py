#!/usr/bin/env python3
"""
Apply v10 migration: Fix assessment_images table - add uploaded_by column
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

load_dotenv()

def get_db_connection():
    """Get database connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "accessibility_dev"),
        user=os.getenv("DB_USER", "hettiera"),
        password=os.getenv("DB_PASSWORD", "hettiera")
    )

def apply_migration():
    """Apply the v10 migration"""
    migration_file = "db_schema/migrations/v10_fix_assessment_images_uploaded_by.sql"
    
    if not os.path.exists(migration_file):
        print(f"Migration file not found: {migration_file}")
        return False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read the migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Applying v10 migration: Fix assessment_images table...")
        
        # Execute the migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ v10 migration applied successfully!")
        
        # Verify the columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='assessment_images' 
            AND column_name IN ('uploaded_by', 'uploaded_at')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        print(f"Verified columns in assessment_images: {[col[0] for col in columns]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def check_table_structure():
    """Check the current structure of assessment_images table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name='assessment_images' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\nCurrent assessment_images table structure:")
        print("Column Name | Data Type | Nullable | Default")
        print("-" * 50)
        for col in columns:
            print(f"{col[0]} | {col[1]} | {col[2]} | {col[3] or 'None'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking table structure: {e}")

if __name__ == "__main__":
    print("🔧 Assessment Images Table Migration Tool")
    print("=" * 50)
    
    # Check current structure
    check_table_structure()
    
    # Apply migration
    if apply_migration():
        print("\n🎉 Migration completed successfully!")
        check_table_structure()
    else:
        print("\n💥 Migration failed!")
        sys.exit(1) 