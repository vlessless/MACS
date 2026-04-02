# MACS: Multi-Agent Autonomous Coding System

## The "Bridge of Observability"

MACS is an autonomous, hierarchical multi-agent framework designed to manage the full Software Development Life Cycle (SDLC). It operates on a **Chain of Command** structure, enforcing rigorous engineering standards through a **Hybrid Consensus** model and a **5-Strike Circuit Breaker** protocol.

This repository represents the core engine, utilizing **Onion Architecture** to ensure the Domain logic remains isolated from infrastructure concerns.

---

## 🏗 System Architecture

MACS follows a strict hierarchical protocol for task execution and code approval:

1.  **Milestone (Major Team Lead):** Defines the high-level roadmap and architectural boundaries.
2.  **Minor Team Lead:** Decomposes milestones into actionable tickets and reviews developer output.
3.  **Developer Agents:** Specialized agents (Backend, Frontend, DevOps) that execute code changes within isolated **Sibling Docker Containers**.
4.  **Integration Agent (The Observer):** Provides a real-time **Thought Trace** via WebSockets, acting as the transparent bridge between the agent hierarchy and the human supervisor.

---

## 🛠 Tech Stack

### Core Runtime
*   **Language:** Python 3.12+
*   **Package Manager:** [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)
*   **Orchestration:** Asyncio-based State Machine

### Infrastructure & Persistence
*   **Web Framework:** FastAPI / Starlette (Asynchronous WebSocket Event Stream)
*   **Database:** PostgreSQL 16+ (Global State & Task Persistence)
*   **ORM:** SQLAlchemy 2.0 (Mapped to Domain Entities via strict mappers)
*   **Message Broker:** Redis (Task Queuing & Pub/Sub for the Event Stream)
*   **Isolation:** Docker Sibling Containers (Host-path mounting for `/var/run/docker.sock`)

### Quality & Validation
*   **Logic Enforcement:** Pydantic V2 (Strict Schema Validation)
*   **Linting/Formatting:** Ruff
*   **Static Typing:** Mypy (Strict mode)
*   **Testing:** Pytest / Pytest-Asyncio

---

## 🚦 Operational Protocols

### 1. The 5-Strike Rule
If a Developer Agent fails a `pytest` suite 5 consecutive times, the system triggers a **HALT**. The Developer must generate a **Post-Mortem JSON Report** (Hypothesis, Observed Error, Blocker), and the task is escalated for **Human Intervention**.

### 2. Hybrid Consensus
*   **TL-1 (Backend)** proposes/reviews code.
*   **TL-2 (DevOps/Architect)** approves.
*   If a disagreement occurs, a 3rd TL is invoked for a **Majority Vote**.

### 3. Stash & Sync (Human-in-the-Loop)
When a human intervenes, the system:
1.  Sends `SIGSTOP` to active containers.
2.  Creates a `human-fix-checkpoint` branch.
3.  Performs a `git diff` upon resumption to re-index agent context.

---

## 🚀 Getting Started

### Prerequisites
*   [uv](https://github.com/astral-sh/uv) installed.
*   Docker & Docker Compose.
*   PostgreSQL & Redis instances.

### Installation
MACS uses `uv` for lightning-fast dependency management:

```bash
# Clone the repository
git clone https://github.com/your-repo/macs.git
cd macs

# Create a virtual environment and sync dependencies
uv venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
uv sync
```

### Running the Integration Observer
The Integration Agent provides the real-time Thought Trace:

```bash
uv run python macs/main.py
```

---

## 📁 Project Structure

```text
/
├── macs/
│   ├── domain/           # Pure Entities, Interfaces, and Enums (No Dependencies)
│   ├── application/      # Orchestrator & Use Case logic
│   ├── infrastructure/   # Persistence (SQLAlchemy), Docker, and Redis adapters
│   └── main.py           # Entry point
├── tests/                # Async test suites
├── pyproject.toml        # Project metadata and Ruff/Mypy/uv config
└── README.md
```

## 📜 Log Structure (Thought Trace)
Every agent action broadcasted via the WebSocket follows this schema:

```json
{
  "timestamp": "ISO-8601",
  "agent": "AgentName",
  "action": "ACTION_TYPE",
  "reason": "Chain of thought explanation",
  "priority": "LOW | MEDIUM | HIGH | CRITICAL",
  "metadata": {}
}
```

---
**Status:** `Development Phase - Ticket 1: Core Domain & Persistence Infrastructure`
**Agent:** `Integration Agent`
**Mission:** `The Bridge of Observability`
