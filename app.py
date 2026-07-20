from email_ingest.gmail_listener import (
    get_gmail_services,
    fetch_unread_message_ids,
    download_raw_message,
)
from email_ingest.parser import parse_raw_email
from email_ingest.features import extract_observations, build_email_context
from agent.react_agent import run_agent



service, creds = get_gmail_services()

ids = fetch_unread_message_ids(service, max_results=5)
print(ids)

if ids:
    raw = download_raw_message(service, ids[0])
    parsed = parse_raw_email(raw, ids[0])

    print("Sender:", parsed["sender_email"])
    print("Domain:", parsed["domain"])
    print("Links:", parsed["links"])
    print("Attachments:", parsed["attachments"])

    observations = extract_observations(parsed)
    context = build_email_context(parsed, observations)

    agent_result = run_agent(context)

    print(agent_result["classification"])
    print(agent_result["confidence"])
    print(agent_result["reasoning"])
