import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import DATABASE_URL
from database.models import get_session, EmailLog, ReasoningTrace

session_factory = get_session(DATABASE_URL)
session = session_factory()

# 1. Can you query by decision type?
phishing_emails = session.query(EmailLog).filter_by(decision="Phishing").all()
print(f"Found {len(phishing_emails)} emails classified as phishing")

# 2. Can you query by confidence threshold?
low_confidence = session.query(EmailLog).filter(EmailLog.confidence < 70).all()
print(f"Found {len(low_confidence)} low-confidence decisions")

# 3. Can you reconstruct a full trace for any email?
if phishing_emails:
    sample = phishing_emails[0]
    trace = (
        session.query(ReasoningTrace)
        .filter_by(email_id=sample.id)
        .order_by(ReasoningTrace.step_number)
        .all()
    )
    print(f"Email {sample.gmail_message_id} has {len(trace)} logged reasoning steps")
else:
    print("No phishing-classified emails found in the database yet.")

session.close()

