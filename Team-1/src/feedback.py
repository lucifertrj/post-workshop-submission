def collect_interactive_feedback(question: str, execution_result: dict) -> dict:
    """Interactive mode: ask the user."""
    if not execution_result["success"]:
        print(f"SQL Error: {execution_result['error']}")
        return {
            "correct": False,
            "expected_output": "query failed with error",
            "sql_feedback": execution_result["error"],
            "failure_type": "sql_error"
        }
    
    print(f"\nResult ({execution_result['rows_returned']} rows):")
    for row in execution_result["result"][:5]:
        print(" ", row)
    if execution_result["rows_returned"] > 5:
        print(f"  ... and {execution_result['rows_returned'] - 5} more rows")
    
    # Implicit: empty result on question expecting data
    question_lower = question.lower()
    if execution_result["rows_returned"] == 0 and any(
        question_lower.startswith(w) for w in ["what", "which", "find", "list", "show", "how many"]
    ):
        print("Note: Query returned 0 rows. This may be unexpected.")
    
    correct = input("\nWas this correct? (y/n): ").strip().lower() == 'y'
    expected = ""
    sql_feedback = ""
    if not correct:
        expected = input("What did you expect? ").strip()
        sql_feedback = input("Any issue with the SQL? (press enter to skip): ").strip()
    
    return {
        "correct": correct,
        "expected_output": expected,
        "sql_feedback": sql_feedback,
        "failure_type": "user_rejected" if not correct else "none"
    }

def collect_batch_feedback(execution_result: dict, gold_result: list) -> dict:
    """Batch mode: compare against BIRD gold SQL output automatically."""
    if not execution_result["success"]:
        return {
            "correct": False,
            "expected_output": str(gold_result),
            "sql_feedback": execution_result["error"],
            "failure_type": "sql_error"
        }
    
    # Sort both for set comparison (BIRD EX metric)
    # Using string representation for simple comparison matching BIRD
    gen = sorted([str(r) for r in execution_result["result"]])
    gold = sorted([str(r) for r in gold_result])
    correct = gen == gold
    
    return {
        "correct": correct,
        "expected_output": str(gold_result) if not correct else "",
        "sql_feedback": "",
        "failure_type": "wrong_result" if not correct else "none"
    }

