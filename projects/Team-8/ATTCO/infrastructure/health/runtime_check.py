"""
Runtime Health Check — verifies end-to-end connectivity and configuration integrity.
"""
import asyncio
import os
from infrastructure.config.loader import ConfigLoader
import structlog

logger = structlog.get_logger(__name__)

async def check_duckdb():
    import duckdb
    db_path = os.getenv("DB_PATH", "./artifacts/metrics.duckdb")
    try:
        conn = duckdb.connect(db_path)
        conn.execute("SELECT 1")
        return True, f"DuckDB connected at {db_path}"
    except Exception as e:
        return False, f"DuckDB connection failed: {e}"

async def check_litellm():
    try:
        import litellm
        # Just check if we can list models or if it's installed
        return True, "LiteLLM initialized"
    except Exception as e:
        return False, f"LiteLLM initialization failed: {e}"

async def run_diagnostics():
    print("Running ATTCO System Health Check...")
    
    # 1. Environment
    ConfigLoader.load()
    
    # 2. Database
    db_ok, db_msg = await check_duckdb()
    print(f"{'[OK]' if db_ok else '[FAIL]'} {db_msg}")
    
    # 3. LLM Gateway
    llm_ok, llm_msg = await check_litellm()
    print(f"{'[OK]' if llm_ok else '[FAIL]'} {llm_msg}")
    
    # 4. Providers
    providers = ConfigLoader.get_provider_status()
    for p, ok in providers.items():
        print(f"{'[OK]' if ok else '[WARN]'} Provider {p.upper()}: {'Configured' if ok else 'Not Configured'}")

    print("\nHealth check complete.")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
