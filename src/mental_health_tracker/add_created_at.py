import os
import sqlite3
from pathlib import Path
from datetime import datetime

def add_created_at_column():
    """
    Add the missing created_at column to the user table
    """
    # Get the database path
    db_path = Path(__file__).parent / 'mental_health.db'
    
    if not db_path.exists():
        print(f"Database file not found at {db_path}")
        # Check instance folder
        instance_db_path = Path(__file__).parent.parent.parent / 'instance' / 'mental_health_tracker.db'
        if instance_db_path.exists():
            db_path = instance_db_path
            print(f"Found database at {db_path}")
        else:
            print(f"Also checked {instance_db_path}, but no database found")
            return False
    
    print(f"Using database at {db_path}")
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists to prevent errors
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current user table columns: {columns}")
        
        if 'created_at' not in columns:
            print("Adding created_at column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN created_at TIMESTAMP")
            
            # Set default values for existing records
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("UPDATE user SET created_at = ? WHERE created_at IS NULL", 
                          (current_time,))
            
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("Column created_at already exists. No migration needed.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False
    finally:
        conn.close()
        
    return True

if __name__ == "__main__":
    print("======= Starting created_at column migration... =======")
    success = add_created_at_column()
    if success:
        print("======= Migration completed successfully! =======")
    else:
        print("======= Migration failed. =======")
    print("Script execution complete. Check the output above for details.") 