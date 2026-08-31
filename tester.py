#!/usr/bin/env python3
"""
=====================================================
HACKATHON TEMPLATE — Track 4
AI Project Manager Agent for Agile Teams
=====================================================
Starter template. Build on top of this.
DO NOT change class interfaces or output format.
"""

import os
import json
import csv
import logging
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

CONFIG = {
    "team_id": os.getenv("TEAM_ID", "VisionX"),
    "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
    "llm_model": os.getenv("LLM_MODEL", "gemini-1.5-flash"),
    "api_base_url": os.getenv("API_BASE_URL"),
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    "sp_dataset_path": os.getenv("SP_DATASET_PATH", "C:/Users/SAMA/Downloads/data.csv"),
    "backlog_path": os.getenv("BACKLOG_PATH", "C:/Users/SAMA/Downloads/agile_ready_backlog.csv"),
    "outputs_path": os.getenv("OUTPUTS_PATH", "C:/Users/SAMA/Downloads/pm_agent_outputs"),
    "stale_days": int(os.getenv("STALE_DAYS", "5")),
    "random_seed": int(os.getenv("RANDOM_SEED", "42")),
}

# ────────────────────────────────
# Helpers
# ────────────────────────────────
def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

def write_json(path: str, data: Any) -> None:
    ensure_dir(str(Path(path).parent))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def safe_text(*parts: Any) -> str:
    return " ".join([str(p) for p in parts if p is not None]).strip()

def safe_split_list(value: Any) -> List[str]:
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]

def safe_parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def safe_parse_date(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

def extract_json_from_text(text: str) -> Optional[Any]:
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        start_candidates = [text.find("["), text.find("{")]
        start_candidates = [i for i in start_candidates if i != -1]
        if not start_candidates:
            return None
        start = min(start_candidates)
        end = max(text.rfind("]"), text.rfind("}"))
        if end == -1 or end <= start:
            return None
        snippet = text[start:end+1]
        try:
            return json.loads(snippet)
        except Exception:
            return None

def call_gemini(prompt: str, max_tokens: int = 800, temperature: float = 0.2) -> Optional[str]:
    api_key = CONFIG.get("gemini_api_key")
    model = CONFIG.get("llm_model", "gemini-1.5-flash")
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    try:
        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        text = parts[0].get("text", "")
        return text.strip() if text else None
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return None

# ────────────────────────────────
# DATA MODELS
# ────────────────────────────────
class IssueType(Enum):
    EPIC = "epic"
    STORY = "story"
    BUG = "bug"
    TASK = "task"
    SUB_TASK = "sub_task"

class IssueStatus(Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"

@dataclass
class Issue:
    issue_id: str
    title: str
    description: str
    issue_type: str
    status: str
    priority: str
    assignee: Optional[str] = None
    team: Optional[str] = None
    story_points: Optional[int] = None
    parent_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    comments: List[Dict] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class GeneratedTicket:
    ticket_id: str
    title: str
    description: str
    issue_type: str
    acceptance_criteria: List[str]
    estimated_story_points: int
    assigned_team: str
    priority: str
    labels: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

@dataclass
class BlockerAlert:
    issue_id: str
    blocker_type: str
    description: str
    severity: str
    recommended_action: str

@dataclass
class DailySummary:
    date: str
    total_issues: int
    in_progress: int
    blocked: int
    completed_today: int
    at_risk: List[Dict]
    blockers: List[BlockerAlert]
    key_updates: List[str]
    action_items: List[str]

def summary_to_text(summary: DailySummary) -> str:
    text = [
        f"Date: {summary.date}",
        f"Total Issues: {summary.total_issues}",
        f"In Progress: {summary.in_progress}",
        f"Blocked: {summary.blocked}",
        f"Completed Today: {summary.completed_today}",
        f"At Risk Issues: {', '.join([a['issue_id'] for a in summary.at_risk])}",
        f"Key Updates: {' | '.join(summary.key_updates)}",
        f"Action Items: {' | '.join(summary.action_items)}"
    ]
    return "\n".join(text)

# ────────────────────────────────
# Backlog Reader
# ────────────────────────────────
class BacklogReader:
    @staticmethod
    def from_csv(filepath: str) -> List[Issue]:
        issues: List[Issue] = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                issues.append(Issue(
                    issue_id=row.get("issue_id", "") or row.get("id", "") or "",
                    title=row.get("title", "") or "",
                    description=row.get("description", "") or "",
                    issue_type=(row.get("issue_type", "story") or "story").lower(),
                    status=(row.get("status", "backlog") or "backlog").lower(),
                    priority=(row.get("priority", "medium") or "medium").lower(),
                    assignee=row.get("assignee") or None,
                    team=row.get("team") or None,
                    story_points=safe_parse_int(row.get("story_points")),
                    parent_id=row.get("parent_id") or None,
                    labels=safe_split_list(row.get("labels")),
                    dependencies=safe_split_list(row.get("dependencies")),
                    created_at=row.get("created_at") or None,
                    updated_at=row.get("updated_at") or None,
                ))
        return issues

    @staticmethod
    def from_json(filepath: str) -> List[Issue]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Issue(**item) for item in data]

    @staticmethod
    def from_api(base_url: str, endpoint: str = "/issues") -> List[Issue]:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [Issue(**item) for item in data]
        except Exception as e:
            logger.error(f"API fetch failed: {e}")
            return []

# ────────────────────────────────
# ABSTRACT INTERFACES
# ────────────────────────────────
class TicketGenerator(ABC):
    @abstractmethod
    def generate_tickets(self, feature_description: str, existing_backlog: List[Issue]) -> List[GeneratedTicket]:
        pass

class StoryPointEstimator(ABC):
    @abstractmethod
    def estimate(self, ticket: GeneratedTicket, historical_data: List[Issue]) -> int:
        pass

class TeamAssigner(ABC):
    @abstractmethod
    def assign_team(self, ticket: GeneratedTicket, teams: Dict[str, List[str]]) -> str:
        pass

class BlockerDetector(ABC):
    @abstractmethod
    def detect_blockers(self, issues: List[Issue]) -> List[BlockerAlert]:
        pass

class SummaryGenerator(ABC):
    @abstractmethod
    def generate_daily_summary(self, issues: List[Issue], blockers: List[BlockerAlert]) -> DailySummary:
        pass

# ────────────────────────────────
# Implementations (LLM + Rule-based)
# ────────────────────────────────
# ... [Insert LLMTicketGenerator, LLMStoryPointEstimator, RuleBasedTeamAssigner, AnalyticsBlockerDetector, LLMSummaryGenerator here]
# Due to space, the full implementations can be copied from your original template (they remain unchanged)

# ────────────────────────────────
# PMAgent
# ────────────────────────────────
class PMAgent:
    def __init__(self):
        self.reader = BacklogReader()
        self.ticket_gen = LLMTicketGenerator()
        self.estimator = LLMStoryPointEstimator()
        self.assigner = RuleBasedTeamAssigner()
        self.blocker_det = AnalyticsBlockerDetector()
        self.summary_gen = LLMSummaryGenerator()
        self.backlog: List[Issue] = []
        ensure_dir(CONFIG.get("outputs_path", "./outputs/"))

    def load_backlog(self, source: str, source_type: str = "csv") -> int:
        if source_type == "csv":
            self.backlog = self.reader.from_csv(source)
        elif source_type == "json":
            self.backlog = self.reader.from_json(source)
        elif source_type == "api":
            self.backlog = self.reader.from_api(source)
        return len(self.backlog)

    def break_down_feature(self, feature_description: str) -> List[GeneratedTicket]:
        tickets = self.ticket_gen.generate_tickets(feature_description, self.backlog)
        for ticket in tickets:
            ticket.estimated_story_points = self.estimator.estimate(ticket, self.backlog)
            ticket.assigned_team = self.assigner.assign_team(ticket)
        write_json(os.path.join(CONFIG.get("outputs_path", "./outputs/"), "assignment_log.json"),
                   [asdict(t) for t in tickets])
        return tickets

    def detect_blockers(self) -> List[BlockerAlert]:
        blockers = self.blocker_det.detect_blockers(self.backlog)
        write_json(os.path.join(CONFIG.get("outputs_path", "./outputs/"), "blocker_report.json"),
                   [asdict(b) for b in blockers])
        write_json(os.path.join(CONFIG.get("outputs_path", "./outputs/"), "dependency_report.json"),
                   getattr(self.blocker_det, "dependency_list_export", []))
        return blockers

    def generate_summary(self) -> DailySummary:
        blockers = self.detect_blockers()
        return self.summary_gen.generate_daily_summary(self.backlog, blockers)

    def export_results(self, tickets: List[GeneratedTicket] = None, blockers: List[BlockerAlert] = None) -> Dict:
        if blockers is None:
            blockers = self.detect_blockers()
        summary = self.generate_summary()
        return {
            "team_id": CONFIG.get("team_id", "VisionX"),
            "track": "track_4_pm_agent",
            "results": {
                "generated_tickets": [asdict(t) for t in (tickets or [])],
                "story_points": {t.ticket_id: t.estimated_story_points for t in (tickets or [])},
                "team_assignments": {t.ticket_id: t.assigned_team for t in (tickets or [])},
                "blockers_detected": [asdict(b) for b in (blockers or [])],
                "dependencies": getattr(self.blocker_det, "dependency_list_export", []),
                "daily_summary": summary_to_text(summary)
            }
        }

# ────────────────────────────────
# MAIN
# ────────────────────────────────
if __name__ == "__main__":
    agent = PMAgent()
    agent.load_backlog(CONFIG["backlog_path"], source_type="csv")
    feature = "Build a user authentication system with login and token-based access"
    tickets = agent.break_down_feature(feature)
    blockers = agent.detect_blockers()
    output = agent.export_results(tickets=tickets, blockers=blockers)
    print(json.dumps(output, indent=2))