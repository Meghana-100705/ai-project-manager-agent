#!/usr/bin/env python3
"""
=====================================================
HACKATHON TEMPLATE — Track 4
AI Project Manager Agent for Agile Teams
=====================================================
Starter template. Build on top of this.
DO NOT change class interfaces or output format.

You are provided:
  - A Jira-like dataset (CSV/JSON) of issues
  - Example API endpoints to fetch issues
  - Ground-truth story points and team ownership for a labeled subset

Required output format for scoring:
{
    "team_id": "your_team_name",
    "track": "track_4_pm_agent",
    "results": {
        "generated_tickets": [...],
        "story_points": {ticket_id: estimated_points},
        "team_assignments": {ticket_id: team_name},
        "blockers_detected": [...],
        "dependencies": [...],
        "daily_summary": "..."
    }
}
=====================================================

"""

import os
import json
import csv
import logging
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

CONFIG = {
    "team_id": os.getenv("TEAM_ID", "VisionX"),       # ← CHANGE THIS
    "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
    "llm_model": os.getenv("LLM_MODEL", "gemini-1.5-flash"),
    "api_base_url": os.getenv("API_BASE_URL"),
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),

    # Dataset A: GitHub story point dataset (bigger, for ML training)
    "sp_dataset_path": os.getenv("SP_DATASET_PATH", "C:/Users/SAMA/Downloads/data.csv"),

    # Dataset B: Backlog dataset (your Jira-like project issues)
    "backlog_path": os.getenv("BACKLOG_PATH", "agile_ready_backlog.csv"),

    # Deliverable artifacts
    "outputs_path": os.getenv("OUTPUTS_PATH", "C:/Users/SAMA/Downloads/pm_agent_outputs"),

    # Stale detection
    "stale_days": int(os.getenv("STALE_DAYS", "5")),

    # Determinism seed
    "random_seed": int(os.getenv("RANDOM_SEED", "42")),
}

# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def ensure_dir(path: str) -> None:
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def write_json(path: str, data: Any) -> None:
    try:
        ensure_dir(str(Path(path).parent))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to write JSON report {path}: {e}")

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
        # supports "YYYY-MM-DD" or ISO formats
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None


# ─────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────
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
    issue_type: str           # epic, story, bug, task
    status: str               # backlog, todo, in_progress, in_review, done, blocked
    priority: str             # critical, high, medium, low
    assignee: Optional[str] = None
    team: Optional[str] = None
    story_points: Optional[int] = None
    parent_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    comments: List[Dict] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # list of issue_ids
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
    blocker_type: str       # dependency, stale, overdue, resource
    description: str
    severity: str           # critical, high, medium, low
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
    # Rigid structure required; exported as STRING
    lines = [
        f"Date: {summary.date}",
        f"Overall sprint progress: total={summary.total_issues}, in_progress={summary.in_progress}, blocked={summary.blocked}, completed_today={summary.completed_today}",
        "",
        "Active Blockers:"
    ]
    if summary.blockers:
        for b in summary.blockers[:20]:
            lines.append(f"- [{b.severity.upper()}] {b.issue_id} ({b.blocker_type}): {b.description} → {b.recommended_action}")
        if len(summary.blockers) > 20:
            lines.append(f"- ...and {len(summary.blockers) - 20} more")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Risks / Red Flags:")
    if summary.at_risk:
        for r in summary.at_risk[:20]:
            lines.append(f"- {r.get('issue_id')}: {r.get('reason')}")
        if len(summary.at_risk) > 20:
            lines.append(f"- ...and {len(summary.at_risk) - 20} more")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Immediate Priority (Next 24h):")
    if summary.action_items:
        for a in summary.action_items[:20]:
            lines.append(f"- {a}")
    else:
        lines.append("- None")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────
# DATA INGESTION — Read backlog from API/CSV/JSON
# ─────────────────────────────────────────────────────
class BacklogReader:
    """Reads issues from multiple data sources."""

    @staticmethod
    def from_csv(filepath: str) -> List[Issue]:
        """Read issues from CSV file."""
        issues: List[Issue] = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                issue = Issue(
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
                )
                issues.append(issue)
        return issues

    @staticmethod
    def from_json(filepath: str) -> List[Issue]:
        """Read issues from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Issue(**item) for item in data]

    @staticmethod
    def from_api(base_url: str, endpoint: str = "/issues") -> List[Issue]:
        """Read issues from REST API."""
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [Issue(**item) for item in data]
        except Exception as e:
            logger.error(f"API fetch failed: {e}")
            return []


# ─────────────────────────────────────────────────────
# ABSTRACT INTERFACES
# ─────────────────────────────────────────────────────
class TicketGenerator(ABC):
    @abstractmethod
    def generate_tickets(self, feature_description: str,
                         existing_backlog: List[Issue]) -> List[GeneratedTicket]:
        """Break down a feature into implementable tickets."""
        pass

class StoryPointEstimator(ABC):
    @abstractmethod
    def estimate(self, ticket: GeneratedTicket, historical_data: List[Issue]) -> int:
        """Estimate story points for a ticket."""
        pass

class TeamAssigner(ABC):
    @abstractmethod
    def assign_team(self, ticket: GeneratedTicket, teams: Dict[str, List[str]]) -> str:
        """Assign a ticket to the most appropriate team."""
        pass

class BlockerDetector(ABC):
    @abstractmethod
    def detect_blockers(self, issues: List[Issue]) -> List[BlockerAlert]:
        """Analyze issues to detect blockers and at-risk items."""
        pass

class SummaryGenerator(ABC):
    @abstractmethod
    def generate_daily_summary(self, issues: List[Issue],
                               blockers: List[BlockerAlert]) -> DailySummary:
        """Generate a daily leadership summary."""
        pass


# ─────────────────────────────────────────────────────
# REFERENCE IMPLEMENTATIONS
# ─────────────────────────────────────────────────────

class LLMTicketGenerator(TicketGenerator):
    """Generate implementable tickets from feature descriptions using deterministic rules."""

    def generate_tickets(self, feature_description: str,
                         existing_backlog: List[Issue]) -> List[GeneratedTicket]:
        tickets: List[GeneratedTicket] = []
        feature = (feature_description or "").lower()
        ticket_counter = 1

        category = "general"
        if any(word in feature for word in ["login", "auth", "authentication", "jwt", "token", "oauth"]):
            category = "authentication"
        elif any(word in feature for word in ["payment", "transaction", "gateway", "razorpay", "stripe"]):
            category = "payment"
        elif any(word in feature for word in ["notification", "email", "sms", "push"]):
            category = "notification"
        elif any(word in feature for word in ["dashboard", "ui", "frontend", "react"]):
            category = "frontend"
        elif any(word in feature for word in ["api", "backend", "server"]):
            category = "backend"

        BLUEPRINTS = {
            "authentication": [
                ("Design Authentication API", "story", "backend", ["auth", "API"]),
                ("Implement Password Hashing & Validation", "task", "backend", ["auth", "security"]),
                ("Implement Token Handling (JWT/Refresh)", "task", "backend", ["auth", "jwt"]),
                ("Add Auth Middleware / Guards", "task", "backend", ["auth", "security"]),
                ("Authentication Testing (Unit + Integration)", "task", "testing", ["auth", "testing"]),
            ],
            "payment": [
                ("Develop Payment API", "story", "backend", ["payment", "API"]),
                ("Design Payment Database Schema", "task", "backend", ["payment", "database"]),
                ("Integrate Payment Provider + Webhooks", "task", "backend", ["payment", "integration"]),
                ("Payment Integration Testing", "task", "testing", ["payment", "testing"]),
            ],
            "notification": [
                ("Build Notification Service API", "story", "backend", ["notification", "API"]),
                ("Integrate Notification Provider Credentials via Env", "task", "devops", ["notification", "security"]),
                ("Implement Notification Module (Templates + Retry)", "task", "backend", ["notification", "integration"]),
                ("Notification Deployment", "task", "devops", ["notification", "deployment"]),
                ("Notification Testing", "task", "testing", ["notification", "testing"]),
            ],
            "frontend": [
                ("Design UI Layout", "story", "frontend", ["UI"]),
                ("Connect UI with Backend API", "task", "frontend", ["integration"]),
                ("Client-side Validation & Accessibility Checks", "task", "frontend", ["UI", "accessibility"]),
                ("Frontend Testing", "task", "testing", ["UI", "testing"]),
            ],
            "backend": [
                ("Develop Backend Logic", "story", "backend", ["backend"]),
                ("Create API Endpoints", "task", "backend", ["API"]),
                ("Add Validation + Error Handling + Logging", "task", "backend", ["backend", "validation"]),
                ("Backend Unit Testing", "task", "testing", ["testing"]),
            ],
            "general": [
                ("Implement Feature Logic", "story", "backend", ["general"]),
                ("Write Unit Tests", "task", "testing", ["testing"]),
                ("Deployment Preparation", "task", "devops", ["deployment"]),
            ],
        }

        selected_blueprint = BLUEPRINTS.get(category, BLUEPRINTS["general"])
        previous_ticket_id = None

        for title, issue_type, team_hint, labels in selected_blueprint:
            acceptance = [
                "Implementation completed",
                "Code reviewed and approved",
                "Test cases executed successfully",
            ]
            if "API" in title:
                acceptance += [
                    "API returns expected response codes",
                    "API validates input and returns clear error messages",
                ]
            if "Database" in title or "Schema" in title:
                acceptance.append("Database schema validated with sample data")
            if "Testing" in title:
                acceptance.append("Edge cases covered")

            ticket_id = "AUTO-" + str(ticket_counter).zfill(3)

            deps: List[str] = []
            if previous_ticket_id:
                deps.append(previous_ticket_id)

            ticket = GeneratedTicket(
                ticket_id=ticket_id,
                title=title,
                description=f"{title} for feature: {feature_description}",
                issue_type=issue_type,
                acceptance_criteria=acceptance,
                estimated_story_points=3 if issue_type == "story" else 2,
                assigned_team=team_hint,
                priority="high" if issue_type == "story" else "medium",
                labels=labels,
                dependencies=deps,
            )
            tickets.append(ticket)
            previous_ticket_id = ticket_id
            ticket_counter += 1

        return tickets


class LLMStoryPointEstimator(StoryPointEstimator):
    """
    ✅ ML-driven story point estimator using TWO datasets:
      Dataset-1 (GitHub): data.csv with columns: point + (concat OR title/user_story)
      Dataset-2 (Backlog): agile_ready_backlog.csv with labeled subset story_points (optional)

    Trains: TF-IDF + Ridge regression (deterministic).
    Fallback: heuristic keyword averages (still uses both datasets).
    """

    FIBONACCI = [1, 2, 3, 5, 8, 13, 21]

    def __init__(self):
        self.dataset_path = CONFIG.get("sp_dataset_path")
        self.model = None
        self.vectorizer = None
        self.trained = False

        # fallback keyword stats
        self.ds_keyword_avg: Dict[str, float] = {}
        self.ds_global_avg: float = 5.0
        self._load_storypoint_dataset_stats()

    def _snap_to_fibonacci(self, raw: float) -> int:
        raw = max(1.0, min(float(raw), 21.0))
        return int(min(self.FIBONACCI, key=lambda x: abs(x - raw)))

    def _load_storypoint_dataset_stats(self) -> None:
        """Build keyword averages from GitHub dataset for fallback (keeps determinism)."""
        if not self.dataset_path or not os.path.exists(self.dataset_path):
            return
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        points_all: List[float] = []
        try:
            with open(self.dataset_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "point" not in row:
                        continue
                    try:
                        p = float(row.get("point"))
                    except Exception:
                        continue

                    if row.get("concat"):
                        text = str(row.get("concat"))
                    else:
                        text = safe_text(row.get("title", ""), row.get("user_story", ""))

                    text = text.strip().lower()
                    if not text:
                        continue

                    points_all.append(p)
                    for w in set(text.split()):
                        totals[w] = totals.get(w, 0.0) + p
                        counts[w] = counts.get(w, 0) + 1

            if points_all:
                self.ds_global_avg = sum(points_all) / len(points_all)

            self.ds_keyword_avg = {w: totals[w] / counts[w] for w in totals if counts[w] >= 20}
        except Exception as e:
            logger.warning(f"Failed to load dataset stats: {e}")

    def _train_if_needed(self, historical_data: List[Issue]) -> None:
        """Train model once. Uses BOTH datasets."""
        if self.trained:
            return
        self.trained = True

        X_text: List[str] = []
        y: List[float] = []

        # A) Backlog labeled subset
        for issue in historical_data:
            if issue.story_points is None:
                continue
            text = safe_text(issue.title, issue.description, " ".join(issue.labels or [])).lower()
            if not text:
                continue
            X_text.append(text)
            y.append(float(issue.story_points))

        # B) GitHub dataset
        if self.dataset_path and os.path.exists(self.dataset_path):
            try:
                with open(self.dataset_path, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    rows = 0
                    for row in reader:
                        if "point" not in row:
                            continue
                        try:
                            p = float(row.get("point"))
                        except Exception:
                            continue

                        if row.get("concat"):
                            text = str(row.get("concat"))
                        else:
                            text = safe_text(row.get("title", ""), row.get("user_story", ""))

                        text = text.strip().lower()
                        if not text:
                            continue

                        X_text.append(text)
                        y.append(float(p))

                        rows += 1
                        if rows >= 5000:
                            break
            except Exception as e:
                logger.warning(f"Could not use GitHub dataset for training: {e}")

        if len(X_text) < 50:
            # not enough data to train; keep fallback only
            self.model = None
            self.vectorizer = None
            return

        try:
            # sklearn is ideal; if unavailable we fallback
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import Ridge

            self.vectorizer = TfidfVectorizer(
                max_features=20000,
                ngram_range=(1, 2),
                lowercase=True
            )
            X = self.vectorizer.fit_transform(X_text)

            self.model = Ridge(alpha=1.0)
            self.model.fit(X, y)

        except Exception as e:
            logger.warning(f"ML training unavailable (sklearn missing?) using fallback. {e}")
            self.model = None
            self.vectorizer = None

    def _fallback_estimate(self, ticket: GeneratedTicket, historical_data: List[Issue]) -> int:
        # Historical averages by type and keyword from backlog
        type_totals, type_counts = {}, {}
        keyword_totals, keyword_counts = {}, {}

        for issue in historical_data:
            if issue.story_points is None:
                continue
            it = (issue.issue_type or "").lower()
            type_totals[it] = type_totals.get(it, 0) + issue.story_points
            type_counts[it] = type_counts.get(it, 0) + 1

            text = safe_text(issue.title, issue.description, " ".join(issue.labels or [])).lower()
            for w in set(text.split()):
                keyword_totals[w] = keyword_totals.get(w, 0) + issue.story_points
                keyword_counts[w] = keyword_counts.get(w, 0) + 1

        avg_by_type = {t: type_totals[t] / type_counts[t] for t in type_totals}
        avg_by_kw = {k: keyword_totals[k] / keyword_counts[k] for k in keyword_totals if keyword_counts[k] >= 2}

        global_avg = (sum(type_totals.values()) / sum(type_counts.values())) if type_counts else self.ds_global_avg
        base = avg_by_type.get((ticket.issue_type or "").lower(), global_avg)

        complexity_weights = {
            "database": 3, "schema": 3, "migration": 3,
            "api": 5, "integration": 5, "webhook": 5,
            "microservice": 8, "ml": 13,
            "deployment": 3,
            "auth": 5, "jwt": 3, "oauth": 5, "security": 5,
        }

        ticket_text = safe_text(ticket.title, ticket.description, " ".join(ticket.labels or [])).lower()

        manual = 0.0
        for k, w in complexity_weights.items():
            if k in ticket_text:
                manual += float(w)

        learned_scores: List[float] = []
        for w in set(ticket_text.split()):
            if w in avg_by_kw:
                learned_scores.append(float(avg_by_kw[w]))
            if w in self.ds_keyword_avg:
                learned_scores.append(float(self.ds_keyword_avg[w]))
        learned = (sum(learned_scores) / len(learned_scores)) if learned_scores else 0.0

        keyword_score = manual if manual >= 8 else (0.7 * manual + 0.3 * learned)
        dep_w = float(len(ticket.dependencies or []))
        ac_w = float(len(ticket.acceptance_criteria or []))

        raw = 0.6 * float(base) + 0.3 * float(keyword_score) + 0.05 * dep_w + 0.05 * ac_w
        return self._snap_to_fibonacci(raw)

    def estimate(self, ticket: GeneratedTicket, historical_data: List[Issue]) -> int:
        self._train_if_needed(historical_data)

        if self.model is not None and self.vectorizer is not None:
            try:
                text = safe_text(ticket.title, ticket.description, " ".join(ticket.labels or [])).lower()
                X = self.vectorizer.transform([text])
                pred = float(self.model.predict(X)[0])
                return self._snap_to_fibonacci(pred)
            except Exception:
                return self._fallback_estimate(ticket, historical_data)

        return self._fallback_estimate(ticket, historical_data)


class RuleBasedTeamAssigner(TeamAssigner):
    """Assign tickets to teams based on labels and skills."""

    TEAM_SKILLS = {
        "frontend": ["UI", "UX", "React", "CSS", "frontend", "design", "accessibility"],
        "backend": ["API", "database", "server", "backend", "microservice", "auth", "jwt", "oauth", "security"],
        "ml_team": ["ML", "model", "training", "data", "pipeline", "AI"],
        "devops": ["deployment", "CI/CD", "infrastructure", "monitoring", "cloud", "secrets"],
        "mobile": ["iOS", "Android", "mobile", "app", "FCM"],
        "testing": ["test", "testing", "qa", "unit", "integration"],
    }

    def assign_team(self, ticket: GeneratedTicket, teams: Dict[str, List[str]] = None) -> str:
        skill_map = teams or self.TEAM_SKILLS
        text = f"{ticket.title} {ticket.description} {' '.join(ticket.labels)}".lower()
        scores: Dict[str, int] = {}
        for team, keywords in skill_map.items():
            scores[team] = sum(1 for kw in keywords if kw.lower() in text)
        if max(scores.values()) == 0:
            return "backend"  # default
        return max(scores, key=scores.get)


# class AnalyticsBlockerDetector(BlockerDetector):
#     """Detect blockers by analyzing issue states and dependencies."""
#     SEQUENCING_RULES = {
#         "development": ["testing", "deployment"],
#         "testing": ["deployment"],
#         "deployment": ["release"]
#     }

#     def __init__(self):
#         self.dependency_list_export: List[Dict[str, Any]] = []

#     def detect_blockers(self, issues: List[Issue]) -> List[BlockerAlert]:
#         blockers: List[BlockerAlert] = []
#         issue_map = {i.issue_id: i for i in issues}
#         dependency_list: List[Dict[str, Any]] = []

#         # Global checks for missing prerequisite patterns
#         all_text = " ".join([(i.title or "") + " " + (i.description or "") for i in issues]).lower()
#         api_found_anywhere = "api" in all_text
#         testing_found_anywhere = "test" in all_text

#         for issue in issues:
#             if issue.status == "blocked":
#                 blockers.append(BlockerAlert(
#                     issue_id=issue.issue_id,
#                     blocker_type="status",
#                     description=issue.title + " is marked as blocked",
#                     severity="high",
#                     recommended_action="Check why this task is blocked"
#                 ))

#             # Dependency edges + alerts
#             for dep_id in (issue.dependencies or []):
#                 if dep_id in issue_map:
#                     dep_issue = issue_map[dep_id]
#                     dependency_list.append({
#                         "issue_id": issue.issue_id,
#                         "issue_title": issue.title,
#                         "depends_on_id": dep_id,
#                         "depends_on_title": dep_issue.title,
#                         "depends_on_status": dep_issue.status
#                     })

#                     if dep_issue.status != "done":
#                         blockers.append(BlockerAlert(
#                             issue_id=issue.issue_id,
#                             blocker_type="dependency",
#                             description=f"Blocked by {dep_issue.issue_id}",
#                             severity="high",
#                             recommended_action=f"Complete {dep_issue.issue_id} first"
#                         ))
#                 else:
#                     dependency_list.append({
#                         "issue_id": issue.issue_id,
#                         "issue_title": issue.title,
#                         "depends_on_id": dep_id,
#                         "depends_on_title": "Unknown",
#                         "depends_on_status": "Unknown"
#                     })
#                     blockers.append(BlockerAlert(
#                         issue_id=issue.issue_id,
#                         blocker_type="dependency",
#                         description=f"Missing dependency reference: {dep_id}",
#                         severity="medium",
#                         recommended_action="Verify dependency ID or create missing prerequisite ticket"
#                     ))

#             text = (safe_text(issue.title, issue.description)).lower()

#             # Missing prerequisites
#             if "integration" in text and not api_found_anywhere:
#                 blockers.append(BlockerAlert(
#                     issue_id=issue.issue_id,
#                     blocker_type="missing_prerequisite",
#                     description="Integration exists but no API task found",
#                     severity="high",
#                     recommended_action="Create API task first"
#                 ))

#             if ("deploy" in text or "deployment" in text) and not testing_found_anywhere:
#                 blockers.append(BlockerAlert(
#                     issue_id=issue.issue_id,
#                     blocker_type="missing_prerequisite",
#                     description="Deployment exists but no testing task found",
#                     severity="high",
#                     recommended_action="Add testing task before deployment"
#                 ))
#             # Sequencing constraints
#             for key, next_steps in self.SEQUENCING_RULES.items():
#                 if key in text:
#                     for next_step in next_steps:
#                         next_issue_found = any(
#                             next_step in safe_text(other.title, other.description).lower()
#                             for other in issues
#                         )
#                         if not next_issue_found:
#                             blockers.append(BlockerAlert(
#                                 issue_id=issue.issue_id,
#                                 blocker_type="sequencing",
#                                 description=f"{key.capitalize()} task exists but no {next_step} task scheduled",
#                                 severity="medium",
#                                 recommended_action=f"Plan {next_step} task after {key}"
#                             ))

#             # Stale tasks
#             if issue.status == "in_progress" and issue.updated_at:
#                 last_update = safe_parse_date(issue.updated_at)
#                 if last_update:
#                     days_old = (datetime.now() - last_update).days
#                     if days_old > CONFIG.get("stale_days", 5):
#                         blockers.append(BlockerAlert(
#                             issue_id=issue.issue_id,
#                             blocker_type="stale",
#                             description="No update for " + str(days_old) + " days",
#                             severity="medium",
#                             recommended_action="Check status with assignee"
#                         ))

#         self.dependency_list_export = dependency_list
#         return blockers




class AnalyticsBlockerDetector(BlockerDetector):
    """
    Detect genuine blockers and dependencies.

    IMPORTANT:
    - Backlog dependencies are reported as dependency edges.
    - A dependency is NOT automatically considered a blocker.
    - Stale/sequencing/missing-prerequisite checks are not treated as
      active blockers.
    - Feature analysis uses the generated AUTO-* tickets separately.
    """

    def __init__(self):
        self.dependency_list_export: List[Dict[str, Any]] = []

    # ---------------------------------------------------------
    # BACKLOG BLOCKER DETECTION
    # ---------------------------------------------------------
    def detect_blockers(self, issues: List[Issue]) -> List[BlockerAlert]:
        """
        Detect only genuine blockers in the supplied backlog.

        A backlog issue is considered an active blocker when:
        1. It is explicitly marked as 'blocked', OR
        2. It depends on another backlog issue that is explicitly blocked.

        We DO NOT classify every unfinished dependency as a blocker.
        We DO NOT classify stale issues as blockers.
        We DO NOT generate global sequencing blockers.
        """

        blockers: List[BlockerAlert] = []
        self.dependency_list_export = []

        if not issues:
            return blockers

        issue_map = {
            str(issue.issue_id).strip(): issue
            for issue in issues
            if issue.issue_id
        }

        seen_blockers = set()
        seen_dependencies = set()

        for issue in issues:

            issue_id = str(issue.issue_id).strip()

            # -------------------------------------------------
            # 1. Explicitly blocked issue
            # -------------------------------------------------
            if str(issue.status).lower() == "blocked":

                blocker_key = (issue_id, "status")

                if blocker_key not in seen_blockers:
                    blockers.append(
                        BlockerAlert(
                            issue_id=issue_id,
                            blocker_type="status",
                            description=(
                                f"{issue.title} is explicitly marked as blocked"
                            ),
                            severity="high",
                            recommended_action=(
                                "Investigate the blocking reason and "
                                "resolve the issue"
                            )
                        )
                    )

                    seen_blockers.add(blocker_key)

            # -------------------------------------------------
            # 2. Dependency analysis
            # -------------------------------------------------
            for dep_id in (issue.dependencies or []):

                dep_id = str(dep_id).strip()

                if not dep_id:
                    continue

                dependency_key = (issue_id, dep_id)

                # Avoid duplicate dependency edges
                if dependency_key in seen_dependencies:
                    continue

                seen_dependencies.add(dependency_key)

                # Known dependency
                if dep_id in issue_map:

                    dep_issue = issue_map[dep_id]

                    self.dependency_list_export.append(
                        {
                            "issue_id": issue_id,
                            "issue_title": issue.title,
                            "depends_on_id": dep_id,
                            "depends_on_title": dep_issue.title,
                            "depends_on_status": dep_issue.status
                        }
                    )

                    # IMPORTANT:
                    # An unfinished dependency is NOT automatically
                    # a blocker.
                    #
                    # Only an explicitly BLOCKED dependency creates
                    # a dependency blocker.
                    if str(dep_issue.status).lower() == "blocked":

                        blocker_key = (issue_id, "dependency", dep_id)

                        if blocker_key not in seen_blockers:

                            blockers.append(
                                BlockerAlert(
                                    issue_id=issue_id,
                                    blocker_type="dependency",
                                    description=(
                                        f"Blocked by {dep_issue.issue_id} "
                                        f"({dep_issue.title})"
                                    ),
                                    severity="high",
                                    recommended_action=(
                                        f"Resolve {dep_issue.issue_id} first"
                                    )
                                )
                            )

                            seen_blockers.add(blocker_key)

                # Unknown dependency reference
                else:

                    self.dependency_list_export.append(
                        {
                            "issue_id": issue_id,
                            "issue_title": issue.title,
                            "depends_on_id": dep_id,
                            "depends_on_title": "Unknown",
                            "depends_on_status": "Unknown"
                        }
                    )

                    # Missing dependency is a data-quality warning,
                    # NOT an active blocker.
                    logger.warning(
                        f"Unknown dependency reference: "
                        f"{issue_id} -> {dep_id}"
                    )

        return blockers

    # ---------------------------------------------------------
    # FEATURE ANALYSIS
    # ---------------------------------------------------------
    def analyze_generated_feature(
        self,
        tickets: List[GeneratedTicket]
    ) -> List[BlockerAlert]:
        """
        Analyze dependencies between newly generated feature tickets.

        Example:

            AUTO-001
                ↓
            AUTO-002
                ↓
            AUTO-003
                ↓
            AUTO-004
                ↓
            AUTO-005

        These are dependencies, NOT blockers.

        Newly generated tickets do not have a real execution status yet,
        so they should not be incorrectly reported as blocked.
        """

        blockers: List[BlockerAlert] = []

        self.dependency_list_export = []

        if not tickets:
            return blockers

        ticket_map = {
            str(ticket.ticket_id).strip(): ticket
            for ticket in tickets
            if ticket.ticket_id
        }

        seen_dependencies = set()

        for ticket in tickets:

            ticket_id = str(ticket.ticket_id).strip()

            for dep_id in (ticket.dependencies or []):

                dep_id = str(dep_id).strip()

                if not dep_id:
                    continue

                dependency_key = (ticket_id, dep_id)

                if dependency_key in seen_dependencies:
                    continue

                seen_dependencies.add(dependency_key)

                # ---------------------------------------------
                # Dependency points to another generated ticket
                # ---------------------------------------------
                if dep_id in ticket_map:

                    dependency_ticket = ticket_map[dep_id]

                    self.dependency_list_export.append(
                        {
                            "issue_id": ticket_id,
                            "issue_title": ticket.title,
                            "depends_on_id": dep_id,
                            "depends_on_title": dependency_ticket.title,
                            "depends_on_status": "planned"
                        }
                    )

                # ---------------------------------------------
                # Unknown dependency
                # ---------------------------------------------
                else:

                    self.dependency_list_export.append(
                        {
                            "issue_id": ticket_id,
                            "issue_title": ticket.title,
                            "depends_on_id": dep_id,
                            "depends_on_title": "Unknown",
                            "depends_on_status": "Unknown"
                        }
                    )

                    logger.warning(
                        f"Generated ticket {ticket_id} has "
                        f"unknown dependency {dep_id}"
                    )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # Generated tickets are newly planned work.
        # Therefore their dependencies are not blockers yet.
        #
        # blockers = [] unless a real execution status exists.
        # -----------------------------------------------------

        return blockers



class LLMSummaryGenerator(SummaryGenerator):
    """Generate daily summaries (deterministic but structured)."""

    def generate_daily_summary(self, issues: List[Issue],
                               blockers: List[BlockerAlert]) -> DailySummary:
        status_counts: Dict[str, int] = {}
        for issue in issues:
            status_counts[issue.status] = status_counts.get(issue.status, 0) + 1

        # At-risk = high/critical blockers
        at_risk = [{"issue_id": b.issue_id, "reason": b.description}
                   for b in blockers if b.severity in ["critical", "high"]]

        # Completed today (best effort)
        today = datetime.now().date()
        completed_today = 0
        for issue in issues:
            if issue.status != "done":
                continue
            dt = safe_parse_date(issue.updated_at)
            if dt and dt.date() == today:
                completed_today += 1

        # Priority next 24 hours
        priority_tasks = []
        for issue in issues:
            if issue.status == "in_progress" or (issue.priority in ["critical", "high"] and issue.status != "done"):
                priority_tasks.append(f"{issue.issue_id}: {issue.title}")

        priority_tasks = priority_tasks[:10]  
            # elif issue.priority in ["critical", "high"] and issue.status != "done":
            #     priority_tasks.append(f"{issue.issue_id}: {issue.title}")
            #     priority_tasks = sorted(set(priority_tasks))[:15]

        key_updates = [
            f"Total issues in sprint: {len(issues)}",
            f"In progress tasks: {status_counts.get('in_progress', 0)}",
            f"Blocked tasks: {status_counts.get('blocked', 0)}",
        ]

        action_items = [
            "Resolve active blockers",
            "Review high-risk issues",
            "Prioritize completion of in-progress tasks",
        ]
        if priority_tasks:
            action_items.append("Next 24h priorities: " + " | ".join(priority_tasks))

        return DailySummary(
            date=datetime.now().strftime("%Y-%m-%d"),
            total_issues=len(issues),
            in_progress=status_counts.get("in_progress", 0),
            blocked=status_counts.get("blocked", 0),
            completed_today=completed_today,
            at_risk=at_risk,
            blockers=blockers,
            key_updates=key_updates,
            action_items=action_items,
        )


# ─────────────────────────────────────────────────────
# MAIN PM AGENT
# ─────────────────────────────────────────────────────
# class PMAgent:
#     """Main Project Manager Agent orchestrator."""

#     def __init__(self):
#         self.reader = BacklogReader()
#         self.ticket_gen = LLMTicketGenerator()
#         self.estimator = LLMStoryPointEstimator()
#         self.assigner = RuleBasedTeamAssigner()
#         self.blocker_det = AnalyticsBlockerDetector()
#         self.summary_gen = LLMSummaryGenerator()
#         self.backlog: List[Issue] = []
#         logger.info("PM Agent initialized")

#         ensure_dir(CONFIG.get("outputs_path", "./outputs/"))

#     def load_backlog(self, source: str, source_type: str = "csv") -> int:
#         """Load backlog from data source. Returns count of issues loaded."""
#         if source_type == "csv":
#             self.backlog = self.reader.from_csv(source)
#         elif source_type == "json":
#             self.backlog = self.reader.from_json(source)
#         elif source_type == "api":
#             self.backlog = self.reader.from_api(source)
#         logger.info(f"Loaded {len(self.backlog)} issues from {source_type}")
#         return len(self.backlog)

#     def break_down_feature(self, feature_description: str) -> List[GeneratedTicket]:
#         """Generate tickets from a high-level feature description."""
#         tickets = self.ticket_gen.generate_tickets(feature_description, self.backlog)

#         assignment_log: List[Dict[str, Any]] = []

#         for ticket in tickets:
#             ticket.estimated_story_points = self.estimator.estimate(ticket, self.backlog)
#             ticket.assigned_team = self.assigner.assign_team(ticket)

#             assignment_log.append({
#                 "ticket_id": ticket.ticket_id,
#                 "title": ticket.title,
#                 "estimated_story_points": ticket.estimated_story_points,
#                 "assigned_team": ticket.assigned_team,
#                 "labels": ticket.labels,
#                 "dependencies": ticket.dependencies
#             })

#         # Deliverable: assignment mapping logs
#         out_dir = CONFIG.get("outputs_path", "./outputs/")
#         write_json(os.path.join(out_dir, "assignment_log.json"), assignment_log)

#         return tickets

#     def detect_blockers(self) -> List[BlockerAlert]:
#         """Scan backlog for blockers and at-risk items."""
#         blockers = self.blocker_det.detect_blockers(self.backlog)

#         # Deliverables: validation reports
#         out_dir = CONFIG.get("outputs_path", "./outputs/")
#         write_json(os.path.join(out_dir, "blocker_report.json"), [asdict(b) for b in blockers])
#         write_json(os.path.join(out_dir, "dependency_report.json"),
#                    getattr(self.blocker_det, "dependency_list_export", []))

#         return blockers

#     def generate_summary(self) -> DailySummary:
#         """Generate daily leadership summary."""
#         blockers = self.detect_blockers()
#         return self.summary_gen.generate_daily_summary(self.backlog, blockers)

#     def export_results(self, tickets: List[GeneratedTicket] = None,
#                    blockers: List[BlockerAlert] = None) -> Dict:
#         """Export results in EVALUATION FORMAT."""
#         if blockers is None:
#             blockers = self.detect_blockers()

#     # Generate summary
#         summary = self.generate_summary()

#         return {
#         "team_id": CONFIG.get("team_id", "VisionX"),
#         "track": "track_4_pm_agent",
#         "results": {
#             "generated_tickets": [asdict(t) for t in (tickets or [])],
#             "story_points": {t.ticket_id: t.estimated_story_points for t in (tickets or [])},
#             "team_assignments": {t.ticket_id: t.assigned_team for t in (tickets or [])},
#             "blockers_detected": [asdict(b) for b in (blockers or [])],

#             # ✅ proper dependency edges (from backlog dependency detection)
#             "dependencies": getattr(self.blocker_det, "dependency_list_export", []),

#             # ✅ must be STRING, not dict
#             "daily_summary": summary_to_text(summary)
#         }
#     }


# # ─────────────────────────────────────────────────────
# # MAIN (Two dataset setup)
# # ─────────────────────────────────────────────────────
# if __name__ == "__main__":
#     agent = PMAgent()

#     # 1️ Load BACKLOG dataset (project issues)
#     agent.load_backlog(CONFIG["backlog_path"], source_type="csv")

#     print("=" * 50)
#     print("AI Project Manager Agent — Demo (Two Dataset Setup)")
#     print("=" * 50)

#     # 2️Generate tickets (ML story-point model uses GitHub dataset + backlog calibration)
#     feature = "Build a user authentication system with login and token-based access"
#     tickets = agent.break_down_feature(feature)

#     print("\nGenerated Tickets:")
#     for t in tickets:
#         print(f"  {t.ticket_id} | {t.title}")
#         print(f"    Story Points: {t.estimated_story_points}")
#         print(f"    Assigned Team: {t.assigned_team}")

#     # 3Detect blockers from BACKLOG dataset
#     blockers = agent.detect_blockers()

#     print("\nDetected Blockers:")
#     for b in blockers:
#         print(f"  ⚠️ [{b.severity.upper()}] {b.issue_id}: {b.description}")

#     # 4️ Export in REQUIRED FORMAT
#     output = agent.export_results(
#         tickets=tickets,
#         blockers=blockers
#     )

#     print("\nFinal Export Output:")
#     print(json.dumps(output, indent=2))

#     print("\nArtifacts saved to:", CONFIG.get("outputs_path"))
#     print(" - assignment_log.json")
#     print(" - blocker_report.json")
#     print(" - dependency_report.json")
#     print(" - sample_export.json")


class PMAgent:
    """
    Main Project Manager Agent orchestrator.

    Separates:
    - historical backlog analysis
    - generated feature tickets
    - feature dependencies
    - feature blockers
    """

    def __init__(self):
        self.reader = BacklogReader()
        self.ticket_gen = LLMTicketGenerator()
        self.estimator = LLMStoryPointEstimator()
        self.assigner = RuleBasedTeamAssigner()
        self.blocker_det = AnalyticsBlockerDetector()
        self.summary_gen = LLMSummaryGenerator()

        # Historical/project backlog
        self.backlog: List[Issue] = []

        # Newly generated feature tickets
        self.generated_tickets: List[GeneratedTicket] = []

        # Feature-specific analysis
        self.feature_blockers: List[BlockerAlert] = []
        self.feature_dependencies: List[Dict[str, Any]] = []

        logger.info("PM Agent initialized")

        ensure_dir(CONFIG.get("outputs_path", "./outputs/"))

    # ---------------------------------------------------------
    # LOAD BACKLOG
    # ---------------------------------------------------------
    def load_backlog(
        self,
        source: str,
        source_type: str = "csv"
    ) -> int:
        """
        Load historical/project backlog.

        This dataset is used for:
        - story point estimation
        - backlog health
        - historical calibration

        It is NOT automatically used as the blocker list for
        the newly generated feature.
        """

        if source_type == "csv":
            self.backlog = self.reader.from_csv(source)

        elif source_type == "json":
            self.backlog = self.reader.from_json(source)

        elif source_type == "api":
            self.backlog = self.reader.from_api(source)

        else:
            raise ValueError(
                f"Unsupported backlog type: {source_type}"
            )

        logger.info(
            f"Loaded {len(self.backlog)} issues from {source_type}"
        )

        return len(self.backlog)

    # ---------------------------------------------------------
    # GENERATE FEATURE TICKETS
    # ---------------------------------------------------------
    def break_down_feature(
        self,
        feature_description: str
    ) -> List[GeneratedTicket]:
        """
        Generate actionable tickets for the requested feature.

        Story-point estimation still uses the historical backlog.
        """

        tickets = self.ticket_gen.generate_tickets(
            feature_description,
            self.backlog
        )

        assignment_log: List[Dict[str, Any]] = []

        for ticket in tickets:

            # ---------------------------------------------
            # Story point estimation
            # ---------------------------------------------
            ticket.estimated_story_points = (
                self.estimator.estimate(
                    ticket,
                    self.backlog
                )
            )

            # ---------------------------------------------
            # Team assignment
            # ---------------------------------------------
            ticket.assigned_team = (
                self.assigner.assign_team(ticket)
            )

            assignment_log.append(
                {
                    "ticket_id": ticket.ticket_id,
                    "title": ticket.title,
                    "estimated_story_points":
                        ticket.estimated_story_points,
                    "assigned_team":
                        ticket.assigned_team,
                    "labels":
                        ticket.labels,
                    "dependencies":
                        ticket.dependencies
                }
            )

        # Save generated tickets
        self.generated_tickets = tickets

        # ---------------------------------------------
        # Feature dependency analysis
        # ---------------------------------------------
        self.feature_blockers = (
            self.blocker_det.analyze_generated_feature(
                tickets
            )
        )

        self.feature_dependencies = (
            getattr(
                self.blocker_det,
                "dependency_list_export",
                []
            )
        )

        # ---------------------------------------------
        # Deliverable: assignment mapping
        # ---------------------------------------------
        out_dir = CONFIG.get(
            "outputs_path",
            "./outputs/"
        )

        write_json(
            os.path.join(
                out_dir,
                "assignment_log.json"
            ),
            assignment_log
        )

        # ---------------------------------------------
        # Deliverable: feature dependency report
        # ---------------------------------------------
        write_json(
            os.path.join(
                out_dir,
                "dependency_report.json"
            ),
            self.feature_dependencies
        )

        return tickets

    # ---------------------------------------------------------
    # BACKLOG BLOCKERS
    # ---------------------------------------------------------
    def detect_blockers(
        self
    ) -> List[BlockerAlert]:
        """
        Detect genuine blockers in the historical backlog.

        This method remains available for backlog-health analysis.
        """

        blockers = self.blocker_det.detect_blockers(
            self.backlog
        )

        out_dir = CONFIG.get(
            "outputs_path",
            "./outputs/"
        )

        write_json(
            os.path.join(
                out_dir,
                "blocker_report.json"
            ),
            [
                asdict(b)
                for b in blockers
            ]
        )

        write_json(
            os.path.join(
                out_dir,
                "dependency_report.json"
            ),
            getattr(
                self.blocker_det,
                "dependency_list_export",
                []
            )
        )

        return blockers

    # ---------------------------------------------------------
    # FEATURE BLOCKERS
    # ---------------------------------------------------------
    def detect_feature_blockers(
        self
    ) -> List[BlockerAlert]:
        """
        Return blockers specifically associated with the
        newly generated feature.

        Newly generated tickets normally have no blockers because
        they are still in the planning stage.
        """

        if not self.generated_tickets:
            return []

        self.feature_blockers = (
            self.blocker_det.analyze_generated_feature(
                self.generated_tickets
            )
        )

        self.feature_dependencies = (
            getattr(
                self.blocker_det,
                "dependency_list_export",
                []
            )
        )

        return self.feature_blockers

    # ---------------------------------------------------------
    # DAILY SUMMARY
    # ---------------------------------------------------------
    def generate_summary(
        self,
        feature_blockers: Optional[List[BlockerAlert]] = None
    ) -> DailySummary:
        """
        Generate leadership summary.

        Backlog statistics still come from the historical backlog,
        while Active Blockers correspond to the requested feature.
        """

        if feature_blockers is None:
            feature_blockers = self.feature_blockers

        return self.summary_gen.generate_daily_summary(
            self.backlog,
            feature_blockers
        )

    # ---------------------------------------------------------
    # EXPORT RESULTS
    # ---------------------------------------------------------
    def export_results(
        self,
        tickets: List[GeneratedTicket] = None,
        blockers: List[BlockerAlert] = None
    ) -> Dict:
        """
        Export final evaluation-safe result.

        IMPORTANT:
        - generated_tickets = requested feature
        - blockers_detected = feature blockers
        - dependencies = generated feature dependencies
        - daily_summary = backlog statistics + feature blockers
        """

        tickets = tickets or self.generated_tickets or []

        # ---------------------------------------------
        # Feature blockers
        # ---------------------------------------------
        if blockers is None:

            if tickets:

                blockers = (
                    self.blocker_det.analyze_generated_feature(
                        tickets
                    )
                )

            else:
                blockers = []

        # ---------------------------------------------
        # Feature dependencies
        # ---------------------------------------------
        if tickets:

            # Rebuild dependency list specifically from
            # generated tickets.
            self.blocker_det.analyze_generated_feature(
                tickets
            )

            feature_dependencies = getattr(
                self.blocker_det,
                "dependency_list_export",
                []
            )

        else:
            feature_dependencies = []

        # ---------------------------------------------
        # Summary
        # ---------------------------------------------
        summary = self.generate_summary(
            feature_blockers=blockers
        )

        # ---------------------------------------------
        # Final output
        # ---------------------------------------------
        return {
            "team_id": CONFIG.get(
                "team_id",
                "VisionX"
            ),

            "track": "track_4_pm_agent",

            "results": {

                "generated_tickets": [
                    asdict(t)
                    for t in tickets
                ],

                "story_points": {
                    t.ticket_id:
                        t.estimated_story_points
                    for t in tickets
                },

                "team_assignments": {
                    t.ticket_id:
                        t.assigned_team
                    for t in tickets
                },

                # Feature-specific blockers only
                "blockers_detected": [
                    asdict(b)
                    for b in blockers
                ],

                # Feature-specific dependencies only
                "dependencies": feature_dependencies,

                # String format required by your schema
                "daily_summary": summary_to_text(
                    summary
                )
            }
        }