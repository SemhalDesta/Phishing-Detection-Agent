import sys
import ast
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import DATABASE_URL
from database.models import get_session, EmailLog, ReasoningTrace


session_factory = get_session(DATABASE_URL)
session = session_factory()


def format_tool_calls(action_input_str: str) -> str:
    """Turns the raw stringified tool_calls list into a readable summary."""
    if not action_input_str or action_input_str == "None":
        return ""

    try:
        tool_calls = ast.literal_eval(action_input_str)
    except (ValueError, SyntaxError):
        return action_input_str  # fallback if parsing fails

    summaries = []
    for call in tool_calls:
        name = call.get("name", "unknown_tool")
        args = call.get("args", {})
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        summaries.append(f"* Called {name}({args_str})")

    return "\n".join(summaries)

log = session.query(EmailLog).filter_by(gmail_message_id="sample-15.eml").first()
if log:
    traces = session.query(ReasoningTrace).filter_by(email_id=log.id).order_by(ReasoningTrace.step_number).all()
    for t in traces:
        print(f"--- Step {t.step_number} ({t.action}) ---")
        if t.thought:
            print(t.thought)
        formatted_calls = format_tool_calls(t.action_input)
        if formatted_calls:
            print(formatted_calls)
        print()
else:
    print("Not logged -- confirm log_email_result actually ran without error during evaluate()")
