import sqlite3
import os

def get_schema(db_id: str, db_dir: str = "data/databases") -> str:
    """Return CREATE TABLE statements for all tables in the database."""
    db_path = os.path.join(db_dir, f"{db_id}.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    schema_parts = []
    for table in tables:
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
        ddl = cursor.fetchone()
        if ddl:
            schema_parts.append(ddl[0])
            
        # Append metadata for categorical text columns
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns_info = cursor.fetchall()
        metadata_lines = []
        
        for col_info in columns_info:
            col_name = col_info[1]
            col_type = col_info[2].upper()
            
            if 'TEXT' in col_type or 'CHAR' in col_type or 'VARCHAR' in col_type:
                try:
                    cursor.execute(f'SELECT COUNT("{col_name}"), COUNT(DISTINCT "{col_name}") FROM "{table}"')
                    total_count, distinct_count = cursor.fetchone()
                    
                    # Heuristics for categorical: distinct values <= 20 and it's less than 10% of total rows
                    # or very small number of distinct values regardless of ratio.
                    if total_count > 0 and (distinct_count <= 20 or distinct_count < total_count * 0.1) and distinct_count <= 50:
                        cursor.execute(f'SELECT DISTINCT "{col_name}" FROM "{table}" WHERE "{col_name}" IS NOT NULL LIMIT 50')
                        distinct_vals = [str(r[0]) for r in cursor.fetchall()]
                        metadata_lines.append(f"-- {table}.{col_name} categorical values: " + ", ".join(distinct_vals))
                except Exception:
                    pass
        
        if metadata_lines:
            schema_parts.append("\n".join(metadata_lines))
            
    conn.close()
    return "\n\n".join(schema_parts)

def execute_sql(db_id: str, sql: str, db_dir: str = "data/databases", timeout: int = 5) -> dict:
    """Execute SQL query safely and return results or error."""
    db_path = os.path.join(db_dir, f"{db_id}.sqlite")
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        return {
            "success": True,
            "result": result,
            "columns": columns,
            "rows_returned": len(result),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": [],
            "columns": [],
            "rows_returned": 0,
            "error": str(e)
        }
