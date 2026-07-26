"""
Main entry point: polls the inbox every POLL_INTERVAL_SECONDS, and for each
new unread email: parse then extract observations then run the ReAct agent then
apply the decision then log everything then mark as read.

Run with: python app.py or py app.py
"""
import time

from config import DATABASE_URL, POLL_INTERVAL_SECONDS
from database.models import EmailLog, ReasoningTrace, get_session
from email_ingest.gmail_listener import (
    get_gmail_services,
    fetch_unread_message_ids,
    download_raw_message,
    mark_as_processed,
)
from email_ingest.parser import parse_raw_email
from email_ingest.features import extract_observations, build_email_context
from agent.react_agent import run_agent
from response.actions import apply_decision


def log_email_result(session, message_id: str, parsed_email: dict, agent_result: dict) -> int:
    """Saves the final decision and the full reasoning trace to the database.
    Returns the new EmailLog's id."""
    email_log = EmailLog(
        gmail_message_id=message_id,
        sender=parsed_email["sender_email"],
        sender_domain=parsed_email["domain"],
        subject=parsed_email["subject"],
        decision=agent_result["classification"],
        confidence=agent_result["confidence"],
        execution_time_seconds=agent_result["execution_time_seconds"],
    )
    session.add(email_log)
    session.flush()  # assigns email_log.id before we need it below

    for i, message in enumerate(agent_result["messages"]):
        content = message.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )

        tool_calls = getattr(message, "tool_calls", None)

        trace = ReasoningTrace(
            email_id=email_log.id,
            step_number=i,
            thought=content,
            action=type(message).__name__,
            action_input=str(tool_calls) if tool_calls else None,
            observation=content,
        )
        session.add(trace)

    session.commit()
    return email_log.id


def process_email(service, message_id: str, session) -> None:
    """Runs one email through the entire pipeline: parse -> observe -> reason
    -> act -> log -> mark as read. Skips messages that were already logged
    in a previous run, to avoid duplicate-key errors and infinite retry loops."""
    existing = session.query(EmailLog).filter_by(gmail_message_id=message_id).first()
    if existing:
        mark_as_processed(service, message_id)
        return

    try:
        raw = download_raw_message(service, message_id)
        parsed = parse_raw_email(raw, message_id)

        observations = extract_observations(parsed)
        context = build_email_context(parsed, observations)

        agent_result = run_agent(context)

        apply_decision(
            service, message_id, agent_result["classification"], agent_result["confidence"]
        )

        log_email_result(session, message_id, parsed, agent_result)

        mark_as_processed(service, message_id)

        print(
            f"[{parsed['sender_email']}] -> {agent_result['classification']} "
            f"({agent_result['confidence']}% confidence)"
        )
    except Exception:
        session.rollback()
        raise


def main():
    service, creds = get_gmail_services()
    session_factory = get_session(DATABASE_URL)

    print(f"Polling inbox every {POLL_INTERVAL_SECONDS}s. Ctrl+C to stop.")

    while True:
        session = session_factory()
        try:
            message_ids = fetch_unread_message_ids(service)
            for message_id in message_ids:
                try:
                    process_email(service, message_id, session)
                except Exception as e:
                    print(f"Error processing message {message_id}: {e}")
        except Exception as e:
            print(f"Error during poll cycle: {e}")
        finally:
            session.close()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()