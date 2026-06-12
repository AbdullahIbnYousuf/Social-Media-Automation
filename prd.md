# Product Requirements Document (PRD)
## Local, Resilient Social Media Automation Engine

---

## 1. Document Control & Metadata

| Field | Value |
| :--- | :--- |
| **Document Title** | Product Requirements Document (PRD): Local Social Media Automation Engine |
| **Author** | Senior Systems Engineer (AI Assistant) |
| **Target Version** | v1.0.0 |
| **Status** | Approved / Operational |
| **Date** | June 12, 2026 |

---

## 2. Executive Summary & Vision

Modern social media scheduling platforms and automation tools (e.g., Zapier, Make.com, high-tier Buffer plans) impose significant subscription costs, limit execution cycles, and present concerns over data privacy. 

The **Local Social Media Automation Engine** is a lightweight, zero-overhead, completely localized automation pipeline. It reads raw content ideas from an embedded SQLite queue, uses the advanced `google-genai` SDK to optimize draft copywriting, and dispatches the final payload to third-party distribution channels (specifically Buffer) via resilient API integrations.

### Key Objectives:
- **Zero Running Costs:** Leverage free/low-cost API tiers (Gemini Flash API) and local orchestration without cloud host server dependencies.
- **Absolute Resilience:** Ensure that flaky internet connections, rate-limits, or API downtime do not cause lost content or database corruption.
- **Deterministic Scheduling:** Run seamlessly as a background process via native OS automation (cron on Unix-like platforms and Task Scheduler on Windows).

---

## 3. Product Features & Scope

### 3.1. Embedded Content Queue (SQLite Engine)
Instead of error-prone CSV or lock-sensitive spreadsheet integrations, the engine maintains state in a single-file SQLite database.

- **State Transitions:** Every content item strictly progresses through a controlled finite-state machine:
  ```mermaid
  stateDiagram-v2
      [*] --> PENDING : User / Script inserts raw_idea
      PENDING --> PROCESSING : Engine starts cycle and locks row
      PROCESSING --> SUCCESS : Content generated and successfully posted
      PROCESSING --> FAILED : LLM or Buffer API failure (max retries exhausted)
      FAILED --> PENDING : Optional manual restart
      SUCCESS --> [*]
  ```
- **Concurrency & Safety:** Uses context managers for database handles and parameterized queries to prevent SQL injection and transaction collisions.

### 3.2. GenAI Copy Optimization
The engine utilizes the Gemini 1.5/2.5 Flash models to transform raw bullet points or rough drafts into platform-specific, engaging posts.

- **Directives:** Reads a system directive instruction from [agent.md](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/agent.md) (or falls back to [agents.md](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/agents.md)) to dictate tone, formatting, hashtag usage, and post lengths.
- **Platform Customization:** Dynamically adjusts the generated outputs depending on the `target_platform` field (e.g., LinkedIn vs. Twitter formatting rules).

### 3.3. API Dispatch (Buffer Integration)
- **GraphQL Protocol:** Fully migrated to Buffer's GraphQL API (`https://api.buffer.com/graphql`) to circumvent REST endpoint limitations, specifically enabling authentications that reject traditional OIDC tokens.
- **Fail-Safe Mutations:** Posts are created atomically using the `createPost` mutation with specific channel profile allocations.

### 3.4. Background Execution & Integration
- Run in standard CLI mode or as a scheduled job.
- Simple operating system bindings ([execution_guide.md](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/execution_guide.md)):
  - **Linux/macOS:** Native cron syntax targeting virtual environment bindings.
  - **Windows:** PowerShell script setup triggering Windows Task Scheduler.

---

## 4. Technical Specifications & Architecture

### 4.1. Technology Stack & Dependencies
The tech stack is designed to be lightweight, fast, and entirely local:

- **Runtime Environment:** Python 3.10+
- **State Management:** SQLite3 (`sqlite3` standard library)
- **AI SDK:** `google-genai` (modern client-based library)
- **Resilience Policy:** `tenacity` (exponential backoff)
- **Http Networking:** `requests` (with connection timeouts)
- **Secrets Management:** `python-dotenv` (reading `.env` mappings)

### 4.2. File Matrix & Structure
The project matches the layout below:
- [src/engine.py](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/src/engine.py) - The main execution orchestration pipeline daemon.
- [src/pipeline.db](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/src/pipeline.db) - SQLite database containing the `content_queue` tables.
- [agents.md](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/agents.md) - System instruction files for agent behavioral directives.
- [requirements.txt](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/requirements.txt) - Locked project dependency specifications.
- [tests/test_buffer_bug_condition.py](file:///c:/Users/My/Desktop/Code/project/Social-Media-Automation/tests/test_buffer_bug_condition.py) - Verification and testing scripts confirming pipeline connectivity.

---

## 5. Non-Functional & Resilience Requirements

### 5.1. Resilience & Network Policy
Network calls to the LLM backend or Buffer API will eventually fail due to transient network drops or rate limiters.
- **Exponential Backoff:** Any block requesting remote services must be decorated with `@retry` policy:
  - **Multiplier:** 1
  - **Min Backoff:** 4 seconds
  - **Max Backoff:** 10 seconds
  - **Max Attempts:** 3 attempts
- **Timeouts:** HTTP network invocations must enforce a strict `timeout=15` boundary to prevent deadlocking the scheduler process.

### 5.2. Strict Logging Guidelines
- Native `print()` statements are forbidden.
- Output logs are piped concurrently to standard console out (`sys.stdout`) and a persistent local text file `logs/pipeline.log`.
- Log format must maintain standard timestamp tags: `%(asctime)s [%(levelname)s] %(message)s`.

### 5.3. Secrets & Key Security
- Under no circumstances will API tokens (`GEMINI_API_KEY`, `BUFFER_ACCESS_TOKEN`, `BUFFER_PROFILE_ID`) be written directly into source files.
- The environment configuration must be parsed at initialization. If a key validation fails, the program logs `critical` severity details and exits with `sys.exit(1)`.

---

## 6. Future Scope & Roadmaps
1. **Multi-Platform Adapters:** Direct API connectors for platforms like LinkedIn, Mastodon, Bluesky, or Threads without intermediary brokers.
2. **Dashboard UI:** A localized web UI (e.g., built with Vite and TailwindCSS) to easily enqueue raw content ideas, modify prompts, and review successes or failures.
3. **Multi-Modal Content Processing:** Support for uploading image or video paths inside the SQLite database to generate and attach assets to social media posts.
