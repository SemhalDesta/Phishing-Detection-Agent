from email_ingest.gmail_listener import (
    get_gmail_services,
    fetch_unread_message_ids,
    download_raw_message,
    
)
from email_ingest.parser import (extract_body_and_links, parse_email)

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