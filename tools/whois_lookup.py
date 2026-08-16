from datetime import datetime
import whois
from langchain_core.tools import tool
from datetime import datetime, timezone

@tool
def check_domain_age(domain: str) -> str:
    """Look up how many days ago a domain was registered.

    Use this when the sender's domain looks unusual, misspelled, or unfamiliar.

    Args:
        domain: the domain to check, e.g. "amaz0n-login.xyz"
    """
    try:
        result = whois.whois(domain)
        creation_date = result.creation_date

        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if creation_date is None:
            return f"No WHOIS creation date found for {domain}."

        # Normalize to timezone-naive, since some registrars return aware
        if creation_date.tzinfo is not None:
            creation_date = creation_date.replace(tzinfo=None)

        age_days = (datetime.now() - creation_date).days
        return f"Domain {domain} was registered {age_days} days ago."

    except Exception as e:
        return f"WHOIS lookup failed for {domain}: {e}"
