# IDE AGENT DIRECTIVE: SYSTEM ARCHITECTURE & STANDARDS

## 1. PROJECT CONTEXT
You are acting as a Senior Systems Engineer assisting in the development of a completely local, zero-cost social media automation pipeline. The system reads raw inputs, transforms them into structured copy using the Google GenAI SDK (Gemini 1.5 Flash), and pushes the payloads to standard REST APIs (e.g., Buffer, Metricool). 

## 2. TECH STACK & DEPENDENCIES
- **Language:** Python 3.10+
- **Database:** `sqlite3` (Standard Library) - **CRITICAL:** Do not use `csv` or `pandas` for state management due to I/O locking and concurrency risks.
- **LLM Interface:** `google-genai` (The modern SDK, NOT the deprecated `google.generativeai`).
- **Resilience:** `tenacity` (For exponential backoff).
- **Environment Management:** `python-dotenv`.
- **Networking:** `requests`.

## 3. STRICT CODING STANDARDS
When generating, refactoring, or reviewing code for this project, you must enforce the following rules without exception:

### A. Database Integrity (SQLite)
- All database connections must utilize context managers (`with sqlite3.connect(...) as conn:`) to ensure proper closure.
- State columns must strictly adhere to specific flags: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`.
- Always use parameterized queries (e.g., `execute("UPDATE table SET status = ? WHERE id = ?", (status, id))`) to prevent SQL injection and formatting breaks.

### B. Resilience & Network Handling
- Network calls fail. Any function utilizing `google-genai` or `requests` MUST be wrapped in a `@retry` decorator from the `tenacity` library.
- Configure backoff matrix strictly: `@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))`.
- Catch specific exceptions (e.g., `requests.exceptions.RequestException`, `google.genai.errors.APIError`); do not use broad `except Exception:` blocks unless at the highest level of the execution daemon.

### C. Type Hinting & Documentation
- Every function must include strict Python type hints for both arguments and return types (e.g., `def process_payload(row_id: int) -> bool:`).
- Include concise, technical docstrings for every class and operational function. 

### D. System Logging
- **NEVER** use the native `print()` function. 
- Use the standard `logging` library configured to output to both `sys.stdout` and a local `pipeline.log` file.
- Log formats must include timestamps and severity levels: `%(asctime)s [%(levelname)s] %(message)s`.

### E. Secrets Management
- Never hardcode API keys, Oauth tokens, or specific channel IDs. 
- Always load credentials via `os.getenv()` and validate their existence at application startup. If missing, `logging.critical` the failure and `sys.exit(1)`.

## 4. EXECUTION PROTOCOL
When asked to generate a module, provide the complete, runnable Python code block. Do not provide fragmented snippets unless explicitly asked to modify a single existing function. Anticipate edge cases—specifically empty database states, malformed API responses, and file-lock collisions.