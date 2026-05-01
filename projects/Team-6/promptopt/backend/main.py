from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import runs, export
from database import init_db

app = FastAPI(title="PromptOpt Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(export.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "PromptOpt API", "docs": "/docs"}

@app.on_event("startup")
def startup_event():
    init_db()
    print("✅ Database initialized")