import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from email_ingest.parser import parse_raw_email
from agents.email_content_agent import run_email_content_agent

raw_bytes = Path("evaluation/dataset/emails/phish_0001.eml").read_bytes()
parsed = parse_raw_email(raw_bytes, message_id="test")
result = run_email_content_agent(parsed)
print(result.risk_score, result.flags, result.reasoning)