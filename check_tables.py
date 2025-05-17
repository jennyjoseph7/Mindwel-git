import sqlite3
import os
from pathlib import Path

def check_tables():
    """
    Check what tables exist in the database.
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
            
            # Get the list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print("\nTables in the database:")
            print("----------------------")
            if tables:
                for table in tables:
                    print(f"- {table[0]}")
                    
                    # For each table, show its schema
                    cursor.execute(f"PRAGMA table_info({table[0]})")
                    columns = cursor.fetchall()
                    print(f"  Schema for {table[0]}:")
                    if columns:
                        print("  cid | name | type | notnull | dflt_value | pk")
                        print("  ---------------------------------------------------")
                        for col in columns:
                            print(f"  {col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
                    else:
                        print("  No columns found!")
                    print()
            else:
                print("No tables found in the database.")
                
            # Close the connection
            conn.close()
            return True
            
    print("No database found at any of the expected locations.")
    return False

if __name__ == "__main__":
    check_tables() 