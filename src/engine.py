import os
import sys
import sqlite3
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None  # type: ignore
    types = None  # type: ignore


LOG_PATH = Path("logs") / "pipeline.log"
DB_PATH = Path("src") / "pipeline.db"
AGENT_PROMPT_PATH = Path("agent.md")
BUFFER_GRAPHQL_URL = os.getenv("BUFFER_GRAPHQL_URL", "https://api.buffer.com/graphql")

CREATE_POST_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
    createPost(input: $input) {
        post {
            id
        }
    }
}
""".strip()


def configure_logging() -> None:
    """Configure logging to stdout and to `logs/pipeline.log`."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_env() -> None:
    """Load environment from .env (if present) and validate required keys.

    Exits the process with a critical log if required secrets are missing.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN")
    buffer_profile = os.getenv("BUFFER_PROFILE_ID")

    if not all([api_key, buffer_token, buffer_profile]):
        logging.critical("Missing one or more required environment variables: GEMINI_API_KEY, BUFFER_ACCESS_TOKEN, BUFFER_PROFILE_ID")
        sys.exit(1)


def resolve_agent_prompt() -> str:
    """Return the system directive from `agent.md` or `agents.md`.

    Exits if neither exists.
    """
    if AGENT_PROMPT_PATH.exists():
        path = AGENT_PROMPT_PATH
    else:
        alt = Path("agents.md")
        if alt.exists():
            path = alt
            logging.info("Using 'agents.md' as runtime directive (agent.md not found).")
        else:
            logging.critical(f"Agent directive missing: checked {AGENT_PROMPT_PATH} and agents.md")
            sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3), reraise=True)
def generate_optimized_copy(raw_idea: str, platform: str, system_directive: str) -> str:
    """Call the GenAI client to generate optimized copy.

    Note: the real API client must be available and credentials valid.
    """
    if genai is None:
        raise RuntimeError("google-genai client is not importable in this environment")

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt_payload = f"[RAW_TEXT]: {raw_idea}\n[TARGET_PLATFORM]: {platform}"
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt_payload,
        config=types.GenerateContentConfig(
            system_instruction=system_directive,
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=800,
        ),
    )

    if getattr(response, "text", None):
        return response.text.strip()
    raise ValueError("Empty response from GenAI model")


@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3), reraise=True)
def dispatch_payload_to_buffer(content: str) -> None:
    """Send the text payload to Buffer using the GraphQL API endpoint."""
    token = os.getenv("BUFFER_ACCESS_TOKEN")
    profile = os.getenv("BUFFER_PROFILE_ID")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "query": CREATE_POST_MUTATION,
        "variables": {"input": {"profileId": profile, "text": content, "shorten": False}},
    }
    res = requests.post(BUFFER_GRAPHQL_URL, json=payload, headers=headers, timeout=15)
    if res.status_code != 200:
        raise requests.exceptions.HTTPError(f"Buffer API error {res.status_code}: {res.text}")

    body = res.json()
    if body.get("errors"):
        raise requests.exceptions.HTTPError(f"Buffer GraphQL errors: {body['errors']}")


def execute_pipeline_cycle() -> None:
    """Main orchestrator: picks PENDING rows, generates content, dispatches, updates DB."""
    system_directive = resolve_agent_prompt()

    if not DB_PATH.exists():
        logging.critical(f"Database not found at {DB_PATH}. Run the init_db bootstrap first.")
        sys.exit(1)

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT id, raw_idea, target_platform FROM content_queue WHERE status = 'PENDING'")
        jobs = cursor.fetchall()

        if not jobs:
            logging.info("No pending jobs found. Exiting.")
            return

        logging.info(f"Found {len(jobs)} pending job(s) to process.")

        for job in jobs:
            job_id = job["id"]
            cursor.execute("UPDATE content_queue SET status = 'PROCESSING' WHERE id = ?", (job_id,))
            conn.commit()

            try:
                final_text = generate_optimized_copy(job["raw_idea"], job["target_platform"], system_directive)
                dispatch_payload_to_buffer(final_text)
                cursor.execute("UPDATE content_queue SET status = 'SUCCESS', generated_output = ? WHERE id = ?", (final_text, job_id))
                conn.commit()
                logging.info(f"Job {job_id} completed successfully.")
            except Exception as e:
                logging.error(f"Job {job_id} failed: {e}")
                cursor.execute("UPDATE content_queue SET status = 'FAILED' WHERE id = ?", (job_id,))
                conn.commit()


if __name__ == "__main__":
    configure_logging()
    logging.info("Starting engine dry run: validating environment and DB")
    load_env()
    execute_pipeline_cycle()
