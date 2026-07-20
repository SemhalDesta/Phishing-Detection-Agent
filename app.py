from email_ingest.gmail_listener import (
    get_gmail_services,
    fetch_unread_message_ids,
    download_raw_message,
)
from email_ingest.parser import (extract_body_and_links, parse_email)
from email_ingest.parser import parse_raw_email
from email_ingest.features import extract_observations, build_email_context
from agent.react_agent import run_agent
from response.actions import apply_decision, get_or_create_label_id



service, creds = get_gmail_services()

ids = fetch_unread_message_ids(service, max_results=5)
print(ids)

if ids:
    raw = download_raw_message(service, ids[0])
    print(raw[:300])
    msg = parse_email(raw)
    print("From:", msg.get("From"))
    print("Subject:", msg.get("Subject"))
    print("Reply-To:", msg.get("Reply-To"))
    result = extract_body_and_links(msg)
    print(result["links"])
    print(result["attachments"])
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

label_id = get_or_create_label_id(service, "QUARANTINE")
print(label_id)

apply_decision(service,  ids[0], agent_result["classification"])
