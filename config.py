import os
from dotenv import load_dotenv

load_dotenv()

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
MAX_REACT_STEPS = int(os.getenv("MAX_REACT_STEPS", "6"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database/logs.db")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
