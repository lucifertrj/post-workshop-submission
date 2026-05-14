# 🛠️ Local Setup & Configuration

This guide provides a deep dive into configuring the ATTCO runtime for local development and research.

## Environment Variables
All configuration is handled via `.env`. Key categories include:

### LLM Providers
- `OPENAI_API_KEY`: Required for core reasoning and baseline.
- `ANTHROPIC_API_KEY`: Optional; used for model-diversity benchmarks.
- `GOOGLE_API_KEY`: Optional; used for Gemini-based evaluation.

### Observability
- `LANGCHAIN_API_KEY`: Enables LangSmith tracing (Project: `ATTCO`).
- `WANDB_API_KEY`: Enables experiment logging to Weights & Biases.

## Directory Structure
- `/artifacts`: Stores execution traces (Parquet), metrics (DuckDB), and calibration snapshots.
- `/optimizer`: Contains all adaptive governance modules.
- `/research`: Evaluation and ablation logic.

## Common Tasks

### Running Ablations
To measure the impact of specific optimizers, use the experiment sweep engine:
```bash
python -m research.experiment_manager --run ablation
```

### Self-Calibration
The system automatically tunes thresholds after benchmark runs. To reset calibration:
```bash
make clean
make setup
```

## Troubleshooting
- **Missing Dependencies**: Run `make install`.
- **Database Errors**: Run `make clean` to reset the DuckDB instance.
- **Provider Timeouts**: Check your API keys and internet connection using `make health`.
