#!/usr/bin/env python3
"""
Quick fix for assessment_images table - add missing columns
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    try:
        # Get database connection
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            conn = psycopg2.connect(db_url)
        else:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "accessibility_dev"),
                user=os.getenv("DB_USER", "hettiera"),
                password=os.getenv("DB_PASSWORD", "hettiera")
            )
        
        cursor = conn.cursor()
        
        print("🔧 Fixing assessment_images table...")
        
        # Add uploaded_by column if it doesn't exist
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='assessment_images' AND column_name='uploaded_by'
                ) THEN
                    ALTER TABLE assessment_images ADD COLUMN uploaded_by VARCHAR(36);
                    
                    -- Set default values for existing records
                    UPDATE assessment_images 
                    SET uploaded_by = (
                        SELECT user_id FROM users WHERE role_id IN (1, 2) LIMIT 1
                    ) 
                    WHERE uploaded_by IS NULL;
                    
                    -- Add foreign key constraint
                    ALTER TABLE assessment_images 
                    ADD CONSTRAINT fk_assessment_images_uploaded_by 
                    FOREIGN KEY (uploaded_by) REFERENCES users(user_id) ON DELETE SET NULL;
                    
                    -- Make NOT NULL after setting defaults
                    ALTER TABLE assessment_images ALTER COLUMN uploaded_by SET NOT NULL;
                END IF;
            END$$;
        """)
        
        # Add uploaded_at column if it doesn't exist
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='assessment_images' AND column_name='uploaded_at'
                ) THEN
                    ALTER TABLE assessment_images ADD COLUMN uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
                END IF;
            END$$;
        """)
        
        conn.commit()
        print("✅ assessment_images table fixed successfully!")
        
        # Verify columns exist
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
        
        print("\n🎉 Database fix completed! Try accessing the location details now.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 