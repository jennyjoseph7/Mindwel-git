import sqlite3
import os
from pathlib import Path

def find_db_files():
    """
    Find all SQLite database files in the project.
    """
    # Current directory
    current_dir = Path('.')
    
    # Find all .db files
    db_files = list(current_dir.glob('**/*.db'))
    
    print(f"Found {len(db_files)} database files:")
    for db_file in db_files:
        print(f"- {db_file}")
        
        # Check if it's a valid SQLite database
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get the list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"  Contains {len(tables)} tables:")
            if tables:
                for table in tables:
                    print(f"  - {table[0]}")
                    
                    # For each table, get column count
                    cursor.execute(f"PRAGMA table_info({table[0]})")
                    columns = cursor.fetchall()
                    print(f"    {len(columns)} columns")
                    
                    # If it's a user table, check for created_at
                    if table[0] == 'user':
                        column_names = [col[1] for col in columns]
                        if 'created_at' in column_names:
                            print("    ✓ created_at column exists")
                        else:
                            print("    ✗ created_at column does NOT exist")
            else:
                print("  No tables found in the database.")
                
            # Close the connection
            conn.close()
            
        except Exception as e:
            print(f"  Error accessing database: {e}")
        
        print()

if __name__ == "__main__":
    find_db_files() 