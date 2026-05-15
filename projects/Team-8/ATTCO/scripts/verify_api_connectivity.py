"""
API Connectivity Verification — tests the validity of configured API keys.
Checks OpenAI, Groq, LangSmith, and Weights & Biases.
"""
import os
import asyncio
from infrastructure.config.loader import ConfigLoader
from litellm import completion
import structlog
import wandb
from langsmith import Client

logger = structlog.get_logger(__name__)

async def test_openai():
    print("[OPENAI] Testing connectivity...")
    try:
        response = await asyncio.to_thread(
            completion,
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("OK OpenAI Response: Successfully connected.")
        return True
    except Exception as e:
        print(f"FAIL OpenAI Error: {e}")
        return False

async def test_groq():
    print("[GROQ] Testing connectivity...")
    try:
        response = await asyncio.to_thread(
            completion,
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("OK Groq Response: Successfully connected.")
        return True
    except Exception as e:
        print(f"FAIL Groq Error: {e}")
        return False

async def test_langsmith():
    print("[LANGSMITH] Testing connectivity...")
    try:
        client = Client()
        projects = list(client.list_projects())
        print(f"OK LangSmith Response: Successfully connected. Found {len(projects)} projects.")
        return True
    except Exception as e:
        print(f"FAIL LangSmith Error: {e}")
        return False

async def test_wandb():
    print("[W&B] Testing connectivity...")
    try:
        api = wandb.Api()
        # Just try to get user info
        user = api.viewer
        username = getattr(user, "username", "unknown")
        print(f"OK W&B Response: Successfully connected as {username}.")
        return True
    except Exception as e:
        print(f"FAIL W&B Error: {e}")
        return False

async def main():
    print("Starting API Connectivity Audit...")
    
    # 1. Load Environment
    ConfigLoader.load()
    
    # Run tests
    results = await asyncio.gather(
        test_openai(),
        test_groq(),
        test_langsmith(),
        test_wandb()
    )
    
    if all(results):
        print("\nALL CORE API CONNECTIVITY TESTS PASSED.")
    else:
        print("\nSOME API CONNECTIVITY TESTS FAILED. Please check your .env file.")

if __name__ == "__main__":
    asyncio.run(main())
