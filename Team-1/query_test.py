import sqlite3
import os

db_dir = "data/databases"
db_path = os.path.join(db_dir, f"california_schools.sqlite")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("")
print(cursor.fetchall())