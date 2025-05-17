# How to Fix the 'no such column: user.created_at' Error

## Problem Summary

The error "no such column: user.created_at" occurs when the SQLAlchemy model has a `created_at` column defined but the actual SQLite database table doesn't have this column. This happens when:

1. The model was updated after the database was created
2. The database wasn't properly migrated after model changes
3. Multiple database files exist with different schemas

## Solution Implemented

We've created and run a migration script that:

1. Locates all SQLite database files in the project
2. Identifies any `user` tables missing the `created_at` column
3. Adds the `created_at` column to those tables
4. Sets a default timestamp value for existing records

The script has been executed and has successfully added the `created_at` column to the database at:
`src\instance\mental_health.db`

## How to Fix This Issue Again

If you encounter this error again, you can:

1. Run the migration script:
   ```
   python add_created_at_column.py
   ```
   
2. Or manually apply the migration to a specific database:
   ```python
   import sqlite3
   from datetime import datetime
   
   # Update the path to your database file
   db_path = 'path/to/your/database.db'
   
   conn = sqlite3.connect(db_path)
   cursor = conn.cursor()
   
   # Check if column already exists
   cursor.execute("PRAGMA table_info(user)")
   columns = [column[1] for column in cursor.fetchall()]
   
   if 'created_at' not in columns:
       # Add the column
       cursor.execute("ALTER TABLE user ADD COLUMN created_at TIMESTAMP")
       
       # Set default values for existing records
       current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
       cursor.execute("UPDATE user SET created_at = ? WHERE created_at IS NULL", 
                      (current_time,))
       
       conn.commit()
       print("Migration completed successfully!")
   else:
       print("Column created_at already exists. No migration needed.")
   
   conn.close()
   ```

## Preventing Future Issues

To prevent similar issues in the future:

1. Use a migration framework like Flask-Migrate for database schema changes.
2. Make sure to run migrations whenever models are updated.
3. Use a single database file to avoid confusion with multiple schemas.
4. Add database schema validation on application startup.

## Multiple Database Files

We noticed that this project has multiple database files with different schemas:

1. `src\instance\mental_health.db` (now updated)
2. `src\mental_health_tracker\mental_health.db` (already had the column)

For consistency, consider standardizing on a single database file, or ensure that all database files are properly migrated when models change.

## Additional Notes

The `User` model already has the `created_at` column defined correctly in the code:

```python
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    # Other columns...
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # More columns...
```

The error occurred because one of the database files was not properly updated to match this schema. 