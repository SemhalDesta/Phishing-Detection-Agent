import requests
from config import VIRUSTOTAL_API_KEY
from langchain_core.tools import tool

VT_DOMAIN_URL = "https://www.virustotal.com/api/v3/domains/{domain}"



@tool
def check_domain_reputation(domain: str) -> str:
    """Check how many security engines flag a domain as malicious.

    Use this after checking domain age, especially if the domain is newly
    registered or the email contains multiple links. This confirms whether
    the domain has an established bad reputation elsewhere on the web.

    Args:
        domain: the domain to check, e.g. "amaz0n-login.xyz"
    """
    if not VIRUSTOTAL_API_KEY:
        return "VirusTotal API key not configured -- skipping this check."

    headers = {"x-apikey": VIRUSTOTAL_API_KEY}

    try:
        response = requests.get(
            VT_DOMAIN_URL.format(domain=domain), headers=headers, timeout=10
        )

        if response.status_code != 200:
            return f"VirusTotal lookup failed for {domain}: HTTP {response.status_code}"

        data = response.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]

        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        total = sum(stats.values())

        return (
            f"{domain}: {malicious} engines flagged malicious, "
            f"{suspicious} flagged suspicious, out of {total} total."
        )

    except Exception as e:
        return f"VirusTotal lookup failed for {domain}: {e}"