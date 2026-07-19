# Architecture

## System Overview

The platform follows a **layered architecture** with clear separation of concerns:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Frontend (SPA)                                │
│  index.html  ·  app.js  ·  api.js  ·  components.js  ·  styles.css  │
│  Chart.js (dashboards)  ·  Monaco Editor (script editing)            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ HTTP/JSON (REST API)
                                 │ JWT Bearer Token Auth
┌────────────────────────────────▼─────────────────────────────────────┐
│                     FastAPI Application (main.py)                     │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   API Layer (REST Endpoints)                    │   │
│  │  Projects · Requirements · Scenarios · Test Cases · Executions  │   │
│  │  Reports · Settings · Auth · Dashboard Metrics · JIRA Import    │   │
│  └──────────────────────────┬─────────────────────────────────────┘   │
│                             │                                         │
│  ┌──────────────────────────▼─────────────────────────────────────┐   │
│  │                    Service Layer (Business Logic)               │   │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐   │   │
│  │  │ProjectSvc  │ │WorkflowSvc   │ │AuthSvc   │ │ReportSvc   │   │   │
│  │  │VaultSvc    │ │ExecutionSvc  │ │JiraSvc   │ │AuditSvc    │   │   │
│  │  │RAGService  │ │RecoveryMgr   │ │BatchMgr   │ │ArtifactMgr │   │   │
│  │  └─────┬──────┘ └──────┬───────┘ └──────────┘ └────────────┘   │   │
│  └───────┬┴───────────────┼───────────────────────────────────────┘   │
│          │                │                                           │
│  ┌───────▼────────────────▼───────────────────────────────────────┐   │
│  │              LangGraph Agent Layer (StateGraph)                 │   │
│  │                                                                 │   │
│  │  SupervisorAgent (routing)                                      │   │
│  │       │                                                         │   │
│  │       ├── RequirementAnalystAgent  ─── FeatureInventoryAgent    │   │
│  │       ├── BacklogCreationAgent     ─── QAStoryAnalyzerAgent     │   │
│  │       ├── ScenarioAgent            ─── HumanApprovalAgent      │   │
│  │       ├── TestCaseAgent            ─── EvaluationAgent          │   │
│  │       ├── PlaywrightAgent                                      │   │
│  │       ├── ExecutionAgent           ─── ExecutionAnalysisAgent   │   │
│  │       ├── DefectManagementAgent    ─── ReportAgent              │   │
│  │       └── JiraSyncAgent                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                             │                                         │
└─────────────────────────────┼─────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────┐
│                   Data / Persistence Layer                             │
│                                                                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  ProjectRepository│  │  PostgresRepo   │  │  SQLAlchemy ORM     │  │
│  │  (JSON file)     │  │  (optional)     │  │  Models + Alembic   │  │
│  └─────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                       │
│  ┌─────────────────┐  ┌──────────────────┐                            │
│  │  Vault JSON     │  │  project_store   │                            │
│  │  (encrypted)    │  │  (JSON DB)       │                            │
│  └─────────────────┘  └──────────────────┘                            │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Layer Descriptions

### 1. Frontend Layer

A single-page application served as static files. No build step — vanilla JS with Chart.js for dashboards and Monaco Editor for script authoring.

- **State management**: In-memory JS objects, no framework
- **API communication**: `api.js` wraps `fetch()` with JWT token handling
- **View switching**: Hash-based routing via `app.js`
- **Components**: `components.js` provides reusable table, modal, card builders

### 2. API Layer

FastAPI application defined in `backend/main.py` (~1300 lines) with:

- **CORS middleware** — open for development
- **Static file mounting** — serves `frontend/` at root
- **JWT authentication** — middleware checks protected routes
- **RBAC enforcement** — `has_permission()` dependency for admin/manager/engineer/viewer roles
- **Background tasks** — long-running file parsing and execution streams

All routes follow the pattern: validate input → call service → serialize response.

### 3. Service Layer

Domain services encapsulate business logic. Key services:

| Service | Responsibility |
|---|---|
| `ProjectService` | Project, requirement, scenario, test case CRUD |
| `WorkflowService` | LangGraph orchestration for all generation/execution operations |
| `AuthService` | JWT creation, password hashing, token refresh |
| `VaultService` | Encrypted credential storage/retrieval |
| `JiraService` | JIRA API integration (stories, bugs, status sync) |
| `ExecutionService` | Test execution orchestration and streaming |
| `ReportService` | JUnit XML report compilation |
| `RAGService` | RAGFlow document upload and retrieval |
| `AuditService` | Audit log writing |
| `RecoveryManager` | Crash recovery for interrupted executions |
| `BatchQueueManager` | Queue management for batch test runs |

### 4. Agent Layer (LangGraph)

The core AI orchestration. A `StateGraph` where each node is an agent implementing `BaseAgent.run(state) -> state`. 

Design principles:
- **State-only communication** — agents never call each other directly
- **Write-only ownership** — each agent modifies only its designated state fields
- **Supervisor routing** — Central agent decides "who runs next" via conditional edges
- **Dependency injection** — `build_graph()` accepts mock agents for testing

### 5. Data Layer

Abstract `ProjectRepository` interface with two implementations:

- **JSON file repository** (`project_repository.py`): Stores all data in `backend/database/project_store.json`. Transactions are atomic per file write.
- **PostgreSQL repository** (`postgres_project_repository.py`): Full SQLAlchemy ORM with connection pooling.

The vault (`backend/database/vault.json`) stores credentials encrypted with `cryptography` Fernet.

---

## Configuration Architecture

```
                     ┌──────────────────────┐
                     │  .env (secrets)       │
                     │  LLM_API_KEY          │
                     │  LANGSMITH_API_KEY    │
                     │  DATABASE_URL         │
                     └──────────┬───────────┘
                                │ overrides
┌───────────────────┐  ┌───────▼────────────┐
│ default_config    │  │  override.yaml     │
│ .yaml (committed) │──┤ (runtime edits)    │
│                   │  │                    │
│ - LLM defaults    │  │ UI settings saves  │
│ - Workflow mode   │  │ write here         │
│ - Thresholds      │  │                    │
└───────────────────┘  └────────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
          ┌──────────────────┐
          │  get_settings()  │
          │  (cached)        │
          └──────────────────┘
```

Precedence: `.env` > `override.yaml` > `default_config.yaml`

---

## Data Flow: Request Through Pipeline

```
Client Request
    │
    ▼
FastAPI Route (e.g., POST /generate-scenarios)
    │
    ▼
WorkflowService.generate_scenarios()
    │
    ├── Fetch requirement from repository
    ├── Build LangGraph with ScenarioAgent
    ├── Invoke graph with WorkflowState
    │       │
    │       ▼
    │   StateGraph
    │   START → SupervisorAgent
    │        → ScenarioAgent (LLM generates scenarios)
    │        → HumanApprovalAgent (check review mode)
    │        → END
    │
    ├── Persist generated scenarios to repository
    └── Return list of Scenario objects
    │
    ▼
FastAPI serializes to ScenarioResponse DTO
    │
    ▼
Client receives JSON response
```

---

## Security Architecture

- **Password storage**: bcrypt hashing via passlib
- **JWT tokens**: python-jose with HS256, configurable expiry
- **Credential vault**: AES encryption via `cryptography.fernet`
- **RBAC**: 4 roles (admin, manager, engineer, viewer) with granular permissions per entity+action
- **Audit trail**: All create/update/delete operations logged with user, timestamp, IP

---

## Scalability Considerations

- **Stateless API**: All state lives in the repository or LangGraph's in-memory execution
- **Async execution**: Long-running Playwright tests use background tasks with SSE-like polling
- **Repository swap**: JSON → PostgreSQL migration requires no code changes beyond config
- **Agent isolation**: Each agent can be independently scaled or replaced
- **Multi-provider LLM**: Provider switch is a config change, no code modification needed
