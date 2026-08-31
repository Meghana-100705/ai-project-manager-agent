from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from track4_pm_agent import PMAgent, CONFIG

app = FastAPI(title="Track 4 PM Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    feature_description: str
    backlog_path: str | None = None
    backlog_type: str = "csv"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/run")
def run_agent(req: RunRequest):
    agent = PMAgent()
    backlog_path = req.backlog_path or CONFIG.get("backlog_path")
    agent.load_backlog(backlog_path, source_type=req.backlog_type)
    tickets = agent.break_down_feature(req.feature_description)
    blockers = agent.detect_blockers()
    return agent.export_results(tickets=tickets, blockers=blockers)