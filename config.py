import os
from dotenv import load_dotenv

load_dotenv()

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5")
MAX_REACT_STEPS = int(os.getenv("MAX_REACT_STEPS", "6"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database/logs.db")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_DATABASE_URL = os.getenv("DEMO_DATABASE_URL", "sqlite:///database/demo_logs.db")
