# 🚀 ATTCO Quickstart Guide

ATTCO (Adaptive Test-Time Compute Optimization) is an advanced research platform for ReAct-based LLM agents.

## 1. Prerequisites
- Python 3.12+
- `pip` or `uv` (recommended)

## 2. Setup
Clone the repository and run the setup command:

```bash
# Install dependencies and initialize environment
make setup
```

## 3. Configuration
1. Copy `.env.example` to `.env`.
2. Add your `OPENAI_API_KEY`.
3. (Optional) Add `LANGCHAIN_API_KEY` for LangSmith tracing.

## 4. Run Benchmark
Execute the default adaptive benchmark suite:

```bash
make benchmark
```

## 5. Launch Dashboard
Visualize optimization performance and Pareto frontiers:

```bash
make run-dash
```

## 6. Health Check
Verify your installation and provider connectivity:

```bash
make health
```

---
For detailed information, see [LOCAL_SETUP.md](./LOCAL_SETUP.md).
