import os
import sys
import sqlite3
from datetime import datetime

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create upload directories
def create_upload_directories():
    from app import app
    os.makedirs(app.config['PROFILE_PICTURES_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)
    print("Created upload directories")

# Add new columns to Employee table
def add_profile_picture_column():
    # Try both possible database locations
    db_paths = ['employees.db', 'instance/employees.db']
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"Using database at {db_path}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            print(f"Tables in database: {table_names}")
            
            # Find the employee table (might be 'employee' or 'Employee')
            employee_table = None
            for table in table_names:
                if table.lower() == 'employee':
                    employee_table = table
                    break
            
            if not employee_table:
                print(f"No employee table found in {db_path}")
                conn.close()
                continue
                
            # Check if profile_picture column exists
            cursor.execute(f"PRAGMA table_info({employee_table})")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            print(f"Columns in {employee_table} table: {column_names}")
            
            if 'profile_picture' not in column_names:
                cursor.execute(f"ALTER TABLE {employee_table} ADD COLUMN profile_picture TEXT")
                print(f"Added profile_picture column to {employee_table} table")
            else:
                print(f"profile_picture column already exists in {employee_table} table")
            
            conn.commit()
            conn.close()
            return True
    
    print("Could not find a valid database file")
    return False

# Create Document table
def create_document_table():
    # Try both possible database locations
    db_paths = ['employees.db', 'instance/employees.db']
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"Using database at {db_path} for document table")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            
            # Find the employee table (might be 'employee' or 'Employee')
            employee_table = None
            for table in table_names:
                if table.lower() == 'employee':
                    employee_table = table
                    break
            
            if not employee_table:
                print(f"No employee table found in {db_path}")
                conn.close()
                continue
            
            # Check if document table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document'")
            if not cursor.fetchone():
                cursor.execute(f'''
                CREATE TABLE document (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES {employee_table} (id)
                )
                ''')
                print("Created Document table")
            else:
                print("Document table already exists")
            
            conn.commit()
            conn.close()
            return True
    
    print("Could not find a valid database file for document table")
    return False

if __name__ == "__main__":
    print("Running database migration for document support...")
    create_upload_directories()
    
    profile_picture_success = add_profile_picture_column()
    document_table_success = create_document_table()
    
    if profile_picture_success and document_table_success:
        print("Migration completed successfully!")
    else:
        print("Migration completed with errors. Please check the logs above.")