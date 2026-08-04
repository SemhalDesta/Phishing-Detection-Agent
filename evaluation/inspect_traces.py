import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import DATABASE_URL
from database.models import get_session, EmailLog, ReasoningTrace


session_factory = get_session(DATABASE_URL)
session = session_factory()

log = session.query(EmailLog).filter_by(gmail_message_id="phish_0025.eml").first()
if log:
    traces = session.query(ReasoningTrace).filter_by(email_id=log.id).order_by(ReasoningTrace.step_number).all()
    for t in traces:
        print(f"--- Step {t.step_number} ({t.action}) ---")
        print(t.thought)
        print()
else:
    print("Not logged -- confirm log_email_result actually ran without error during evaluate()")
