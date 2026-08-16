import ast
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config import DATABASE_URL, DEMO_DATABASE_URL, DEMO_MODE
from database.models import get_session, EmailLog, ReasoningTrace


active_db_url = DEMO_DATABASE_URL if DEMO_MODE else DATABASE_URL




def format_tool_calls(action_input_str: str) -> str:
    """Turns the raw stringified tool_calls list into a readable summary."""
    if not action_input_str or action_input_str == "None":
        return ""
    try:
        tool_calls = ast.literal_eval(action_input_str)
    except (ValueError, SyntaxError):
        return action_input_str
    summaries = []
    for call in tool_calls:
        name = call.get("name", "unknown_tool")
        args = call.get("args", {})
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        summaries.append(f"* Called {name}({args_str})")
    return "\n".join(summaries)


st.set_page_config(page_title="Phishing Agent Dashboard", layout="wide")
st.title("Phishing Detection Agent — Monitoring Dashboard")

session_factory = get_session(active_db_url)
session = session_factory()

emails = session.query(EmailLog).order_by(EmailLog.created_at.desc()).all()

if not emails:
    st.info("No processed emails yet. Run app.py or evaluation/run_eval.py first.")
else:
    df = pd.DataFrame([{
        "id": e.id,
        "sender": e.sender,
        "sender_domain": e.sender_domain,
        "subject": e.subject,
        "decision": e.decision,
        "confidence": e.confidence,
        "time (s)": round(e.execution_time_seconds, 2) if e.execution_time_seconds else None,
        "processed_at": e.created_at,
    } for e in emails])

    st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Reasoning trace")

    selected_id = st.selectbox("View reasoning trace for email ID:", df["id"])
    if selected_id:
        traces = (
            session.query(ReasoningTrace)
            .filter(ReasoningTrace.email_id == selected_id)
            .order_by(ReasoningTrace.step_number)
            .all()
        )
        for t in traces:
            with st.expander(f"Step {t.step_number}: {t.action}", expanded=False):
                if t.thought:
                    st.write(t.thought)
                formatted_calls = format_tool_calls(t.action_input)
                if formatted_calls:
                    st.code(formatted_calls, language=None)
                if not t.thought and not formatted_calls:
                    st.caption("(no content for this step)")

session.close()