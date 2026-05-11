import json
import logging
from ollama import chat

# Optional: Disable verbose logger logs for standard runs
logging.basicConfig(level=logging.INFO)

def call_llm(system_prompt: str, user_content: str, expect_json: bool = True) -> str:
    """Wrapper to call locally hosted Qwen2.5-coder via Ollama."""
    try:
        response = chat(
            model='qwen2.5-coder',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content}
            ],
            format='json' if expect_json else None
        )
        return response.message.content or ""
    except Exception as e:
        logging.error(f"Ollama LLM call failed: {e}")
        return ""

def call_llm_json(system_prompt: str, user_content: str) -> dict:
    """Wrapper to force strict JSON parsing from the model."""
    raw = call_llm(system_prompt, user_content, expect_json=True)
    raw = raw.strip()
    
    # Strip markdown formatting
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON. Raw string: {raw}")
        return {}
