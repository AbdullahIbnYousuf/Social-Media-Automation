# Execution Guide: Deploying the Bulletproof Local Social Media Automation Engine

This document provides explicit, step-by-step technical instructions for deploying the localized automation pipeline. Follow this protocol sequentially to transition from an empty directory to a fully automated, resilient background daemon.

---

## Phase 1: Environment & Directory Configuration

Run these terminal commands to establish an isolated workspace, configure the project directory matrix, create a Python virtual environment, and install necessary production dependencies.

```bash
# 1. Establish project root and child directories
mkdir -p social_automation_engine/src social_automation_engine/logs
cd social_automation_engine

# 2. Initialize necessary workspace tracking assets
touch src/engine.py .env agent.md agents.md requirements.txt

# 3. Provision isolated Python execution sandbox
python3 -m venv venv

# 4. Activate the sandbox environment context
# On Linux/macOS:
source venv/bin/activate
# On Windows PowerShell:
# .\\venv\\Scripts\\Activate.ps1
```

Write the exact package requirements into your `requirements.txt` file:

```text
google-genai==0.1.1
tenacity==8.3.0
python-dotenv==1.0.1
requests==2.32.3
```

Install the dependencies within your active environment:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Phase 2: Database Initialization (SQLite)

To avoid data corruption or state collisions from file locking, we use SQLite instead of flat CSV files. Execute the following standalone snippet once to bootstrap your local tracking repository.

Create a temporary initialization file named `init_db.py`:

```python
import sqlite3

def bootstrap_database():
    with sqlite3.connect("src/pipeline.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_idea TEXT NOT NULL,
                target_platform TEXT NOT NULL,
                status TEXT CHECK(status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED')) DEFAULT 'PENDING',
                generated_output TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test mock validation row
        cursor.execute("""
            INSERT INTO content_queue (raw_idea, target_platform) 
            VALUES (?, ?)
        """, ("Testing the local SQLite implementation loop using the new google-genai SDK architecture.", "linkedin"))
        conn.commit()
        print("Database 'src/pipeline.db' initialized with ACID state tracking safely.")

if __name__ == "__main__":
    bootstrap_database()
```

Run the script and remove it safely:
```bash
python init_db.py
rm init_db.py
```

---

## Phase 3: Populating Environment Constants

Open your `.env` configuration file and pass your explicit environment configurations. Ensure no whitespace or quote tags wrap your security tokens.

```ini
GEMINI_API_KEY=AIzaSyYourValidatedStudioDeveloperAPIKeyHere
BUFFER_ACCESS_TOKEN=tok_yourSecuredOauthBearerTokenForBufferAPI
BUFFER_PROFILE_ID=664fccYourSpecificTargetChannelProfileID
BUFFER_GRAPHQL_URL=https://api.buffer.com/graphql
```

---

## Phase 4: Production Core Implementation (`src/engine.py`)

Populate `src/engine.py` with the complete, error-resilient automation script block. This codebase implements context managers for database security, exponential backoff for network limits, and dynamic compilation of the standalone runtime agent layout.

```python
import os
import sys
import sqlite3
import logging
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure unified logging output profiles
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

load_dotenv()

# System prerequisite assertions
API_KEY = os.getenv("GEMINI_API_KEY")
BUFFER_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE = os.getenv("BUFFER_PROFILE_ID")
BUFFER_GRAPHQL_URL = os.getenv("BUFFER_GRAPHQL_URL", "https://api.buffer.com/graphql")
DB_PATH = "src/pipeline.db"
AGENT_PROMPT_PATH = "agent.md"

CREATE_POST_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
    createPost(input: $input) {
        post {
            id
        }
    }
}
""".strip()

if not all([API_KEY, BUFFER_TOKEN, BUFFER_PROFILE]):
    logging.critical("Missing system critical operational environments within .env layout.")
    sys.exit(1)

# Initialize modern GenAI tracking client interface
client = genai.Client(api_key=API_KEY)

def load_runtime_agent_directive() -> str:
    """Reads the runtime system instruction prompt from external file constraint."""
    if not os.path.exists(AGENT_PROMPT_PATH):
        logging.critical(f"System constraint rule document missing at path: {AGENT_PROMPT_PATH}")
        sys.exit(1)
    with open(AGENT_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3), reraise=True)
def generate_optimized_copy(raw_idea: str, platform: str, system_directive: str) -> str:
    """Requests deterministic copy optimization from Gemini 1.5 Flash with backoff loops."""
    prompt_payload = f"[RAW_TEXT]: {raw_idea}\n[TARGET_PLATFORM]: {platform}"
    
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt_payload,
        config=types.GenerateContentConfig(
            system_instruction=system_directive,
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=800
        )
    )
    if response.text:
        return response.text.strip()
    raise ValueError("Empty string payload response evaluated via API gate.")

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3), reraise=True)
def dispatch_payload_to_buffer(content: str) -> None:
    """Pushes processed text variants safely over Buffer's GraphQL API."""
    headers = {
        "Authorization": f"Bearer {BUFFER_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": CREATE_POST_MUTATION,
        "variables": {
            "input": {
                "profileId": BUFFER_PROFILE,
                "text": content,
                "shorten": False
            }
        }
    }
    res = requests.post(BUFFER_GRAPHQL_URL, json=payload, headers=headers, timeout=15)
    if res.status_code != 200:
        raise requests.exceptions.HTTPError(f"Server rejection status {res.status_code}: {res.text}")

    response_body = res.json()
    if response_body.get("errors"):
        raise requests.exceptions.HTTPError(f"GraphQL mutation rejected: {response_body['errors']}")

def execute_pipeline_cycle():
    """Orchestrates transaction iterations via isolated sqlite context loops safely."""
    system_directive = load_runtime_agent_directive()
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Track pending units processing requirements
        cursor.execute("SELECT id, raw_idea, target_platform FROM content_queue WHERE status = 'PENDING'")
        jobs = cursor.fetchall()
        
        if not jobs:
            logging.info("Zero transactional entries matched PENDING rules states. Engine resting.")
            return
            
        logging.info(f"Bootstrapping processing pipeline loops across {len(jobs)} assigned rows.")
        
        for job in jobs:
            job_id = job['id']
            logging.info(f"Transitioning execution row sequence scope state pointer -> ID: {job_id}")
            
            # Atomic phase lock reservation
            cursor.execute("UPDATE content_queue SET status = 'PROCESSING' WHERE id = ?", (job_id,))
            conn.commit()
            
            try:
                # Execution optimization step
                final_text = generate_optimized_copy(job['raw_idea'], job['target_platform'], system_directive)
                
                # Distribution relay step
                dispatch_payload_to_buffer(final_text)
                
                # Clear processing completion flag state mutations
                cursor.execute(
                    "UPDATE content_queue SET status = 'SUCCESS', generated_output = ? WHERE id = ?",
                    (final_text, job_id)
                )
                conn.commit()
                logging.info(f"Completed operational pipeline routing lifecycle successfully for ID: {job_id}")
                
            except Exception as e:
                logging.error(f"Operational breakdown error processed along entry trace sequence reference tracking ID {job_id}: {e}")
                cursor.execute("UPDATE content_queue SET status = 'FAILED' WHERE id = ?", (job_id,))
                conn.commit()

if __name__ == "__main__":
    logging.info("Core transactional script daemon initial call initialized manually or programmatically.")
    execute_pipeline_cycle()
```

---

## Phase 5: Automated Cron/Scheduler Integration

### Linux/macOS Native Automation
Access user cron system configuration matrix parameters:
```bash
crontab -e
```
Append the strict script tracking rule pattern below to trigger processing execution flows once a day at exactly 09:00 AM:
```text
0 9 * * * cd /absolute/path/to/social_automation_engine && ./venv/bin/python src/engine.py >> logs/cron_error.log 2>&1
```

### Windows Native Task Scheduler Automation
Execute this administrative block inside a terminal PowerShell window instance to bind execution tracking schedules programmatically:
```powershell
$TaskAction = New-ScheduledTaskAction -Execute "C:\absolute\path\to\social_automation_engine\venv\Scripts\python.exe" -Argument "C:\absolute\path\to\social_automation_engine\src\engine.py"
$TaskTrigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
Register-ScheduledTask -TaskName "LocalResilientSocialAutomationEngine" -Action $TaskAction -Trigger $TaskTrigger -Description "ACID-Compliant Local Content Distribution Engine Background Daemon"
```
