from datetime import datetime
import whois
from langchain_core.tools import tool

@tool
def check_domain_age(domain: str) -> str:
    """Looks up how many days ago a domain was registered."""
    try:
        result = whois.whois(domain)
        creation_date = result.creation_date

        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if creation_date is None:
            return f"No WHOIS creation date found for {domain}."

        age_days = (datetime.now() - creation_date).days
        return f"Domain {domain} was registered {age_days} days ago."

    except Exception as e:
        return f"WHOIS lookup failed for {domain}: {e}"

