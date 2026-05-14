"""
Bootstrap Script — prepares the ATTCO environment for first-time use.
Handles directory initialization, environment verification, and health checks.
"""
import os
import sys
from pathlib import Path
from infrastructure.config.loader import ConfigLoader

def bootstrap():
    print("Initializing ATTCO Platform...")
    
    # 1. Load Environment
    ConfigLoader.load()
    
    # 2. Initialize Artifacts Directory
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    print(f"Artifacts directory initialized: {artifacts_dir.absolute()}")
    
    # 3. Check Providers
    providers = ConfigLoader.get_provider_status()
    print("\n--- Provider Status ---")
    for p, active in providers.items():
        status = "ACTIVE" if active else "MISSING"
        print(f"{p.upper():<10}: {status}")
        
    # 4. Check Observability
    langsmith = bool(os.getenv("LANGCHAIN_API_KEY"))
    wandb = bool(os.getenv("WANDB_API_KEY"))
    
    print("\n--- Observability Status ---")
    print(f"LangSmith : {'ENABLED' if langsmith else 'DISABLED (Traces will be local only)'}")
    print(f"W&B       : {'ENABLED' if wandb else 'DISABLED'}")
    
    # 5. Validation
    if not providers["openai"]:
        print("\nCRITICAL: OPENAI_API_KEY not found in .env.")
        print("Please copy .env.example to .env and add your key.")
        sys.exit(1)
        
    print("\nATTCO is ready for execution.")
    print("Run 'make benchmark' to start evaluation.")

if __name__ == "__main__":
    bootstrap()
