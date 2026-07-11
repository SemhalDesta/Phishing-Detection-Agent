import re
from langchain_core.tools import tool

@tool
def check_spf_dkim(authentication_results_header: str) -> str:
    """Check the SPF and DKIM authentication results for this email.

    Use this to confirm whether the sending server was actually authorized
    to send on behalf of the claimed domain. A "fail" on either result is a
    strong phishing signal, especially when combined with other suspicious
    observations like a display-name/domain mismatch or urgency language.

    Args:
        authentication_results_header: the raw value of the email's
            "Authentication-Results" header.
    """
    if not authentication_results_header:
        return "No Authentication-Results header found."

    header_lower = authentication_results_header.lower()

    spf_match = re.search(r"spf=(\w+)", header_lower)
    dkim_match = re.search(r"dkim=(\w+)", header_lower)

    spf_result = spf_match.group(1) if spf_match else "not found"
    dkim_result = dkim_match.group(1) if dkim_match else "not found"

    return f"SPF: {spf_result}, DKIM: {dkim_result}"