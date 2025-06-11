#!/usr/bin/env python3
"""
Cleanup partially applied migration and apply the corrected version
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
    # Try Railway connection first, then local
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    else:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "accessibility_dev"),
            user=os.getenv("DB_USER", "hettiera"),
            password=os.getenv("DB_PASSWORD", "hettiera")
        )

def cleanup_partial_migration():
    """Clean up any partially applied changes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🧹 Cleaning up partially applied migration...")
        
        # Remove uploaded_by column if it exists (with wrong type)
        cleanup_sql = """
        DO $$
        BEGIN
            -- Drop foreign key constraint if it exists
            IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
                      WHERE constraint_name = 'fk_assessment_images_uploaded_by') THEN
                ALTER TABLE assessment_images DROP CONSTRAINT fk_assessment_images_uploaded_by;
            END IF;
            
            -- Drop uploaded_by column if it exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='assessment_images' AND column_name='uploaded_by') THEN
                ALTER TABLE assessment_images DROP COLUMN uploaded_by;
            END IF;
            
            -- Drop uploaded_at column if it exists  
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='assessment_images' AND column_name='uploaded_at') THEN
                ALTER TABLE assessment_images DROP COLUMN uploaded_at;
            END IF;
            
            -- Drop indexes if they exist
            DROP INDEX IF EXISTS idx_assessment_images_uploaded_by;
            DROP INDEX IF EXISTS idx_assessment_images_detail_id;
            DROP INDEX IF EXISTS idx_assessment_images_location_set_id;
        END$$;
        """
        
        cursor.execute(cleanup_sql)
        conn.commit()
        print("✅ Cleanup completed successfully!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def apply_corrected_migration():
    """Apply the corrected migration"""
    migration_file = "db_schema/migrations/v10_fix_assessment_images_uploaded_by.sql"
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read the migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("🔧 Applying corrected v10 migration...")
        
        # Execute the migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Corrected migration applied successfully!")
        
        # Verify the columns exist with correct types
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name='assessment_images' 
            AND column_name IN ('uploaded_by', 'uploaded_at')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        print("✅ Verified columns:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error applying corrected migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def check_final_structure():
    """Check the final table structure"""
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
        print("\n📋 Final assessment_images table structure:")
        print("Column Name | Data Type | Nullable | Default")
        print("-" * 60)
        for col in columns:
            print(f"{col[0]} | {col[1]} | {col[2]} | {col[3] or 'None'}")
        
        # Check specifically for our new columns
        uploaded_by_exists = any(col[0] == 'uploaded_by' and 'character varying' in col[1] for col in columns)
        uploaded_at_exists = any(col[0] == 'uploaded_at' for col in columns)
        
        print(f"\n📊 Column verification:")
        print(f"uploaded_by (VARCHAR): {'✅ EXISTS' if uploaded_by_exists else '❌ MISSING'}")
        print(f"uploaded_at: {'✅ EXISTS' if uploaded_at_exists else '❌ MISSING'}")
        
        cursor.close()
        conn.close()
        return uploaded_by_exists and uploaded_at_exists
        
    except Exception as e:
        print(f"❌ Error checking final structure: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Assessment Images Migration Cleanup & Fix Tool")
    print("=" * 60)
    
    # Step 1: Cleanup partial migration
    if not cleanup_partial_migration():
        print("💥 Cleanup failed!")
        sys.exit(1)
    
    # Step 2: Apply corrected migration
    if not apply_corrected_migration():
        print("💥 Corrected migration failed!")
        sys.exit(1)
    
    # Step 3: Verify final structure
    if check_final_structure():
        print("\n🎉 Migration fixed and applied successfully!")
        print("🚀 Your assessment images issue should now be resolved!")
    else:
        print("\n💥 Final verification failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 