import sqlite3
import os
from pathlib import Path
from datetime import datetime

def find_db_with_user_table():
    """
    Find all databases with a 'user' table that's missing the created_at column.
    """
    current_dir = Path('.')
    dbs_to_update = []
    
    # Find all .db files
    db_files = list(current_dir.glob('**/*.db'))
    
    print(f"Found {len(db_files)} database files. Checking for user tables...")
    
    for db_file in db_files:
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check if this database has a user table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
            if cursor.fetchone():
                # Check if the user table has a created_at column
                cursor.execute("PRAGMA table_info(user)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'created_at' not in columns:
                    print(f"Found database at {db_file} with user table missing created_at column")
                    dbs_to_update.append(db_file)
                else:
                    print(f"Database at {db_file} already has created_at column")
            
            conn.close()
            
        except Exception as e:
            print(f"Error accessing {db_file}: {e}")
    
    return dbs_to_update

def add_created_at_column(db_path):
    """
    Add the missing created_at column to the user table
    """
    print(f"\nUpdating database at {db_path}")
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add the created_at column
        print("Adding created_at column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN created_at TIMESTAMP")
        
        # Set default values for existing records
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE user SET created_at = ? WHERE created_at IS NULL", 
                      (current_time,))
        
        conn.commit()
        print(f"Successfully added created_at column to {db_path}")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'created_at' in columns:
            print("Verification successful: created_at column exists")
        else:
            print("Verification failed: created_at column not found after migration")
            
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False
    finally:
        conn.close()
        
    return True

if __name__ == "__main__":
    print("======= Starting created_at column migration... =======")
    
    dbs_to_update = find_db_with_user_table()
    
    if not dbs_to_update:
        print("No databases found that need updating.")
    
    success = True
    for db_path in dbs_to_update:
        if not add_created_at_column(db_path):
            success = False
    
    if success and dbs_to_update:
        print("======= Migration completed successfully! =======")
    elif not dbs_to_update:
        print("======= No migration needed =======")
    else:
        print("======= Migration failed for some databases. =======")
    
    print("Script execution complete. Check the output above for details.") 