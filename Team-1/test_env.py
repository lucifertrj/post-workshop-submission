from src.executor import get_schema, execute_sql

def test_executor():
    db_id = "california_schools"
    print(f"Testing schema extraction for {db_id}...")
    schema = get_schema(db_id)
    print(f"Schema extracted, length: {len(schema)} characters")
    
    print("\nTesting simple SELECT query...")
    sql = "SELECT * FROM frpm LIMIT 3;"
    res = execute_sql(db_id, sql)
    if res["success"]:
        print(f"Success! Columns: {res['columns']}")
        print(f"Rows returned: {res['rows_returned']}")
    else:
        print(f"Failed: {res['error']}")
        print("Note: If the DB doesn't exist, this is expected if we just want a test. Let me check what DBs are present.")

if __name__ == "__main__":
    test_executor()
