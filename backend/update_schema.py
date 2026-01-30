import sqlite3
import os

DB_PATH = "standards.db"

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    
    if column_name not in columns:
        print(f"Adding column {column_name} to {table_name}...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    else:
        print(f"Column {column_name} already exists in {table_name}.")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        add_column_if_not_exists(cursor, "standards", "publishing_department", "VARCHAR")
        add_column_if_not_exists(cursor, "standards", "implementation_date", "VARCHAR")
        
        conn.commit()
        print("Schema update completed.")
    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
