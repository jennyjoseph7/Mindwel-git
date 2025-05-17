import sqlite3
import os
from pathlib import Path

def verify_schema():
    """
    Verify the user table schema in the database.
    """
    # List of potential database paths to check
    db_paths = [
        Path('instance/mental_health_tracker.db'),
        Path('src/mental_health_tracker/mental_health.db'),
        Path('instance/mental_health.db')
    ]
    
    # Try each path
    for db_path in db_paths:
        if db_path.exists():
            print(f"Found database at {db_path}")
            
            # Connect to the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get the schema info for the user table
            cursor.execute("PRAGMA table_info(user)")
            columns = cursor.fetchall()
            
            print("\nUser table schema:")
            print("-------------------")
            print("cid | name | type | notnull | dflt_value | pk")
            print("---------------------------------------------------")
            for col in columns:
                print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
                
            # Specifically check if created_at column exists
            column_names = [col[1] for col in columns]
            print("\nColumn names:", column_names)
            
            if 'created_at' in column_names:
                print("\nThe created_at column EXISTS in the user table.")
            else:
                print("\nThe created_at column DOES NOT EXIST in the user table.")
                
            # Close the connection
            conn.close()
            return True
            
    print("No database found at any of the expected locations.")
    return False

if __name__ == "__main__":
    verify_schema() 