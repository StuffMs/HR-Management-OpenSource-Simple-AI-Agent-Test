import sqlite3
import os

# Path to the database file
db_path = 'instance/employees.db'

# Check if the database file exists
if not os.path.exists(db_path):
    print(f"Database file {db_path} not found.")
    exit(1)

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if employee_id column exists in user table
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]

if 'employee_id' not in column_names:
    print("Adding employee_id column to user table...")
    cursor.execute("ALTER TABLE user ADD COLUMN employee_id INTEGER")
    conn.commit()
    print("Column added successfully.")
else:
    print("employee_id column already exists in user table.")

# Check if drive_profile_pic_id and drive_folder_id columns exist in employee table
cursor.execute("PRAGMA table_info(employee)")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]

if 'drive_profile_pic_id' not in column_names:
    print("Adding drive_profile_pic_id column to employee table...")
    cursor.execute("ALTER TABLE employee ADD COLUMN drive_profile_pic_id TEXT")
    conn.commit()
    print("drive_profile_pic_id column added successfully.")
else:
    print("drive_profile_pic_id column already exists in employee table.")

if 'drive_folder_id' not in column_names:
    print("Adding drive_folder_id column to employee table...")
    cursor.execute("ALTER TABLE employee ADD COLUMN drive_folder_id TEXT")
    conn.commit()
    print("drive_folder_id column added successfully.")
else:
    print("drive_folder_id column already exists in employee table.")

# Check if document table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document'")
if not cursor.fetchone():
    print("Creating document table...")
    cursor.execute("""
        CREATE TABLE document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            drive_file_id TEXT,
            FOREIGN KEY (employee_id) REFERENCES employee (id)
        )
    """)
    conn.commit()
    print("Document table created successfully.")
else:
    # Check if drive_file_id column exists in document table
    cursor.execute("PRAGMA table_info(document)")
    doc_columns = [column[1] for column in cursor.fetchall()]
    
    if 'drive_file_id' not in doc_columns:
        print("Adding drive_file_id column to document table...")
        cursor.execute("ALTER TABLE document ADD COLUMN drive_file_id TEXT")
        conn.commit()
        print("drive_file_id column added to document table.")
    else:
        print("drive_file_id column already exists in document table.")

# Close the connection
conn.close()
print("Database migration completed.")