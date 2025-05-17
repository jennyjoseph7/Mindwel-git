import os
import sys
import sqlite3

def check_mood_entries():
    """Check if mood entries exist in the database and print them"""
    try:
        # Connect to the database
        conn = sqlite3.connect('src/mental_health_tracker/mental_health.db')
        cursor = conn.cursor()
        
        # Check if mood_entries table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mood_entries'")
        if not cursor.fetchone():
            print("mood_entries table does not exist")
            return
        
        # Get column names
        cursor.execute("PRAGMA table_info(mood_entries)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Table columns: {columns}")
        
        # Get all mood entries
        cursor.execute("SELECT * FROM mood_entries ORDER BY date_created DESC")
        entries = cursor.fetchall()
        
        if not entries:
            print("No mood entries found in the database")
            return
        
        print(f"Found {len(entries)} mood entries:")
        for entry in entries:
            # Create a dictionary with column names as keys
            entry_dict = {columns[i]: entry[i] for i in range(len(columns))}
            print(entry_dict)
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_mood_entries() 