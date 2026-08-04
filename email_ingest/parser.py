import email
from email.message import Message
from email.utils import parseaddr
from bs4 import BeautifulSoup
from email import policy

def parse_email(raw_message) -> email.message.Message:
    """Parses a raw email message into an email.message.Message object."""
    try:
        return email.message_from_bytes(raw_message, policy=policy.default)
    except Exception as e:
        print(f"An error occurred while parsing the email: {e}")
        return None



def extract_sender_info(from_header)-> tuple:
    """
    Extract the sender's display name, email address, and domain
    from a Gmail 'From' header.
    """
    if not from_header:
        return None, None, None

    try:
        name, email_address = parseaddr(from_header)

        domain = None
        if email_address and "@" in email_address:
            domain = email_address.split("@")[-1].lower()

        return name, email_address, domain

    except Exception as e:
        print(f"Error extracting sender info: {e}")
        return None, None, None

def extract_body_and_links(msg) -> dict:
    """Extracts plain text, HTML body, links, and attachment names from a Message."""
    body_plain = ""
    body_html = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                filename = part.get_filename()
                if filename:
                    attachments.append(filename)
            elif content_type == "text/plain":
                body_plain += part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html":
                body_html += part.get_payload(decode=True).decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(errors="ignore")
            if msg.get_content_type() == "text/html":
                body_html = decoded
            else:
                body_plain = decoded

    links = []
    if body_html:
        soup = BeautifulSoup(body_html, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True) if a.get("href")]

    return {
        "body_plain": body_plain,
        "body_html": body_html,
        "links": links,
        "attachments": attachments,
    }


def parse_raw_email(raw_bytes: bytes, message_id: str) -> dict:
    """Parses raw email bytes into a single structured dict."""
    msg = parse_email(raw_bytes)
    if msg is None:
        return None

    name, sender_email, domain = extract_sender_info(msg.get("From"))
    body_data = extract_body_and_links(msg)
    headers = dict(msg.items())

    return {
        "message_id": message_id,
        "subject": msg.get("Subject"),
        "sender_name": name,
        "sender_email": sender_email,
        "domain": domain,
        "body_plain": body_data["body_plain"],
        "body_html": body_data["body_html"],
        "links": body_data["links"],
        "attachments": body_data["attachments"],
        "headers": headers,
    }
