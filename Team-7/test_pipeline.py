import builtins
import os
from main import run_interaction

# Mock inputs to allow automated test of the CLI logic
input_sequence = [
    "y", # Was this correct?
]
input_idx = 0

def mock_input(prompt=""):
    global input_idx
    print(prompt, end="")
    if input_idx < len(input_sequence):
        val = input_sequence[input_idx]
        input_idx += 1
        print(val)
        return val
    print("n")
    return "n"

builtins.input = mock_input

def test():
    print("Testing the full ACE logic...")
    db_id = "california_schools"
    question = "List the top 3 schools by enrollment."
    evidence = ""
    # Clear logs and playbooks for clean test
    if os.path.exists(f"playbooks/{db_id}_playbook.txt"):
        os.remove(f"playbooks/{db_id}_playbook.txt")
        
    res = run_interaction(question, db_id, evidence)
    print("Run completed successfully!")
    print(res.keys())

if __name__ == "__main__":
    test()
