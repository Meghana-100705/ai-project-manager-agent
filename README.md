# 🤖 AI Project Manager Agent

> Intelligent backlog analysis and AI-powered project planning for agile development teams.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Netlify-success?style=for-the-badge)](https://imaginative-kulfi-e22c03.netlify.app/)
[![Backend](https://img.shields.io/badge/Backend-Render-blue?style=for-the-badge)](https://ai-project-manager-agent.onrender.com)
[![API Docs](https://img.shields.io/badge/API-Swagger-orange?style=for-the-badge)](https://ai-project-manager-agent.onrender.com/docs)

---

## 🚀 Live Demo

### 🌐 Frontend
**https://imaginative-kulfi-e22c03.netlify.app/**

### ⚙️ Backend API
**https://ai-project-manager-agent.onrender.com**

### 📚 Swagger API Documentation
**https://ai-project-manager-agent.onrender.com/docs**

---

## 📌 Overview

The **AI Project Manager Agent** is an intelligent project-management system that converts a high-level feature description into an actionable software-development plan.

Instead of manually breaking down a feature into tasks, estimating effort, assigning teams, and identifying dependencies, the agent automatically performs these activities and presents the results through an interactive dashboard.

### Example

A user can enter:

> "Build a secure user authentication system with registration, login, password hashing, JWT authentication and role-based access control."

The agent analyzes the feature and generates:

- Development tickets
- Story-point estimates
- Team assignments
- Priorities
- Acceptance criteria
- Task dependencies
- Blocker analysis
- Feature-level project summary

---

## ✨ Key Features

### 🎫 1. Intelligent Ticket Generation

The agent breaks a high-level feature into actionable development tasks.

Each generated ticket contains:

- Ticket ID
- Title
- Description
- Issue type
- Story points
- Assigned team
- Priority
- Labels
- Acceptance criteria
- Dependencies

Example:

```text
AUTO-001
Design Authentication API

Type: Story
Team: Backend
Priority: High
Story Points: 2
```

---

### 📊 2. Story Point Estimation

The agent estimates the effort required for each generated ticket.

The dashboard provides:

```text
Total Tickets
Total Story Points
High Priority Tickets
```

This helps teams quickly understand the estimated workload for a feature.

---

### 👥 3. Intelligent Team Assignment

Tickets are automatically assigned to the most appropriate development team based on the ticket's content and technical requirements.

Supported teams include:

- `frontend`
- `backend`
- `ml_team`
- `devops`
- `mobile`
- `testing`

#### Example

For an authentication feature:

```text
Authentication API              → backend
Password Hashing                → backend
JWT Token Handling              → backend
Authentication Middleware      → backend
Authentication Testing          → testing
```

The system uses rule-based technical skill matching to make these assignments.

---

### 🔗 4. Dependency Detection

The agent identifies relationships between generated tasks.

Example:

```text
AUTO-002
    ↓
AUTO-001

AUTO-003
    ↓
AUTO-002

AUTO-004
    ↓
AUTO-003

AUTO-005
    ↓
AUTO-004
```

This creates a clear execution order for the development team.

---

### ⚠️ 5. Blocker Detection

The system analyzes the generated feature work for potential blockers and risks.

The dashboard displays:

```text
Blockers Detected
```

If no blockers are identified:

```text
No blockers detected 🎉
```

Feature-specific blocker analysis prevents unrelated backlog issues from being incorrectly presented as blockers for the newly requested feature.

---

### 📋 6. Feature-Level Executive Summary

The agent generates a concise summary specifically for the requested feature.

Example:

```text
Feature Analysis Summary

Generated Tickets: 5
Total Story Points: 11
High Priority Tickets: 1
Dependencies: 4
Active Blockers: 0

Team Distribution:
- backend: 4 ticket(s)
- testing: 1 ticket(s)

Immediate Priorities:
- AUTO-001: Design Authentication API
- AUTO-002: Implement Password Hashing & Validation
- AUTO-003: Implement Token Handling
- AUTO-004: Add Auth Middleware
- AUTO-005: Authentication Testing

Active Blockers:
- None detected
```

---

### 📁 7. Backlog Analysis

The system can load an existing project backlog and use it as part of the project-management workflow.

Supported backlog formats:

- CSV
- JSON

The backend processes the backlog and combines it with feature-level analysis.

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │      User / PM       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   React Frontend     │
                    │      Netlify         │
                    └──────────┬───────────┘
                               │
                               │ REST API
                               ▼
                    ┌──────────────────────┐
                    │     FastAPI API      │
                    │       Render         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     PMAgent          │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
      ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
      │ Ticket      │   │ Team         │   │ Dependency   │
      │ Generation  │   │ Assignment   │   │ Detection    │
      └─────────────┘   └──────────────┘   └──────────────┘
                               │
                               ▼
                       ┌──────────────┐
                       │   Blocker    │
                       │   Analysis   │
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Project      │
                       │ Summary      │
                       └──────────────┘
```

---

## 🔄 Workflow

```text
Feature Description
        │
        ▼
Feature Analysis
        │
        ▼
Task Breakdown
        │
        ├──► Story Point Estimation
        │
        ├──► Team Assignment
        │
        ├──► Priority Assignment
        │
        ├──► Acceptance Criteria
        │
        ├──► Dependency Detection
        │
        └──► Blocker Detection
                │
                ▼
        Feature Summary
                │
                ▼
        Interactive Dashboard
```

---

## 🛠️ Tech Stack

### Frontend

- React
- JavaScript
- Vite
- HTML
- CSS

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### Project Management / AI Logic

- PMAgent
- Rule-based ticket generation
- Rule-based team assignment
- Dependency analysis
- Blocker detection
- Story-point estimation

### Data

- CSV
- JSON

### Deployment

- Netlify — Frontend
- Render — Backend

---

## 📂 Project Structure

```text
pm_agent/
│
├── api_server.py
├── track4_pm_agent.py
├── agile_ready_backlog.csv
├── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd pm_agent
```

### 2. Create a Python environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Activate it on macOS/Linux:

```bash
source venv/bin/activate
```

### 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI server

```bash
python -m uvicorn api_server:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start the frontend (optional, for local dev)

```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 API Usage

### Health Check

**Endpoint**

```text
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

---

### Analyze a Feature

**Endpoint**

```text
POST /run
```

**Request**

```json
{
  "feature_description": "Build a secure user authentication system with registration, login, password hashing, JWT authentication and role-based access control",
  "backlog_path": null,
  "backlog_type": "csv"
}
```

**Response**

The API returns:

```text
Generated Tickets
Story Points
Team Assignments
Blockers
Dependencies
Feature Summary
```

---

## 💡 Example Use Cases

The agent can analyze features such as:

### Authentication

```text
Build a secure user authentication system with registration,
login, password hashing, JWT authentication and role-based
access control.
```

### Analytics Dashboard

```text
Build a responsive React dashboard with charts, filters,
dark mode, and mobile-friendly navigation.
```

### Recommendation System

```text
Build an AI-powered product recommendation system that
analyzes user browsing and purchase history to generate
personalized product recommendations.
```

### Online Learning Platform

```text
Build an online learning platform where users can register,
browse courses, enroll in courses, track learning progress,
and receive notifications.
```

---

## 📈 Example Output

For an authentication feature, the system can generate:

| Ticket   | Task                          | Team    | Priority | Points |
| -------- | ------------------------------ | ------- | -------- | -----: |
| AUTO-001 | Design Authentication API      | backend | High     |      2 |
| AUTO-002 | Password Hashing & Validation  | backend | Medium   |      1 |
| AUTO-003 | JWT/Refresh Token Handling     | backend | Medium   |      3 |
| AUTO-004 | Authentication Middleware      | backend | Medium   |      2 |
| AUTO-005 | Authentication Testing         | testing | Medium   |      3 |

**Total:**

```text
Tickets: 5
Story Points: 11
Teams: 2
Dependencies: 4
Blockers: 0
```

---

## 🎯 Problem We Solve

Traditional project planning often requires a project manager or developer to manually:

1. Understand a feature
2. Break it into tasks
3. Estimate effort
4. Assign teams
5. Define dependencies
6. Identify blockers
7. Communicate priorities

The AI Project Manager Agent automates this initial planning process and provides a structured, actionable plan within seconds.

---

## 🌟 Why This Project?

The goal is to make software project planning:

- Faster
- More structured
- More consistent
- Easier to understand
- More actionable for development teams

Instead of starting with an empty backlog, teams can start with an automatically generated implementation plan.

---

## 👥 Team

**VisionX**

**Track:** Track 4 — AI Project Manager Agent

---

## 🔮 Future Improvements

Potential future enhancements include:

- LLM-powered ticket generation
- Advanced effort estimation
- Historical sprint analytics
- Automatic sprint planning
- Gantt chart generation
- Jira integration
- GitHub Issues integration
- Slack/Teams notifications
- Learning-based team assignment
- Advanced risk prediction
- Automatic backlog prioritization

---

## 📜 License

This project was developed as part of a hackathon project by **Team VisionX**.
