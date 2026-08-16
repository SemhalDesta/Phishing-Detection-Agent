"""
One-off utility: creates a sanitized copy of the evaluation database for
public deployment (Streamlit Cloud demo), stripping real sender addresses
and subjects while preserving decisions, confidence scores, and full
reasoning traces -- the actually interesting content for a demo.

Run with: python deploy/create_demo_db.py
"""
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import EmailLog

SOURCE_DB = Path(__file__).resolve().parent.parent / "database" / "logs.db"
DEMO_DB = Path(__file__).resolve().parent.parent / "database" / "demo_logs.db"

shutil.copy(SOURCE_DB, DEMO_DB)

engine = create_engine(f"sqlite:///{DEMO_DB}")
Session = sessionmaker(bind=engine)
session = Session()

for email in session.query(EmailLog).all():
    email.sender = f"sender_{email.id}@example.com"
    email.sender_domain = "example.com"
    email.subject = f"[Redacted subject #{email.id}]"

session.commit()
session.close()
print(f"Demo database created at {DEMO_DB} with sanitized sender/subject fields.")