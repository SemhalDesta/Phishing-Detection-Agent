from email.utils import parseaddr
from typing import Dict
from bs4 import BeautifulSoup
import re


KNOWN_BRANDS = {
    "paypal": {
        "keywords": ["paypal"],
        "domain": "paypal.com",
    },
    "amazon": {
        "keywords": ["amazon"],
        "domain": "amazon.com",
    },
    "microsoft": {
        "keywords": ["microsoft", "office365", "outlook"],
        "domain": "microsoft.com",
    },
    "google": {
        "keywords": ["google", "gmail"],
        "domain": "google.com",
    },
    "apple": {
        "keywords": ["apple", "icloud"],
        "domain": "apple.com",
    },
    "netflix": {
        "keywords": ["netflix"],
        "domain": "netflix.com",
    },
}


URGENCY_PHRASES = [
    "urgent",
    "verify your account",
    "act now",
    "suspended",
    "click below",
    "immediately",
    "confirm your identity",
    "unusual activity",
    "limited time",
    "your account will be closed",
]


# Feature 1
def calculate_urgency_score(parsed_email: dict) -> dict:
    """Counts urgency-style phishing phrases in the email body."""

    combined_text = (
        parsed_email.get("body_plain", "")
        + " "
        + parsed_email.get("body_html", "")
    ).lower()

    matched_phrases = [
        phrase for phrase in URGENCY_PHRASES
        if phrase in combined_text
    ]

    return {
        "urgency_score": len(matched_phrases),
        "matched_phrases": matched_phrases,
    }


# Feature 2
def reply_to_mismatch(from_header: str, reply_to_header: str) -> bool:
    """Flags when Reply-To domain differs from sender domain."""

    if not from_header or not reply_to_header:
        return False

    try:
        _, sender_email = parseaddr(from_header)
        _, reply_to_email = parseaddr(reply_to_header)

        if "@" not in sender_email or "@" not in reply_to_email:
            return False

        sender_domain = sender_email.split("@")[-1].lower()
        reply_to_domain = reply_to_email.split("@")[-1].lower()

        return sender_domain != reply_to_domain

    except Exception as e:
        print(f"Error checking reply-to mismatch: {e}")
        return False


# Feature 3
def check_links(parsed_email: dict) -> dict:
    """Counts links and checks HTTPS usage."""

    links = parsed_email.get("links", [])

    if not links:
        return {
            "link_count": 0,
            "all_links_https": True
        }

    all_https = all(
        link.lower().startswith("https://")
        for link in links
    )

    return {
        "link_count": len(links),
        "all_links_https": all_https
    }


# Feature 4
def check_attachments(parsed_email: dict) -> dict:
    """Counts attachments and checks suspicious file types."""

    attachments = parsed_email.get("attachments", [])

    suspicious_extensions = {
        ".exe",
        ".bat",
        ".cmd",
        ".scr",
        ".js",
        ".vbs",
        ".jar"
    }

    suspicious_attachments = [
        att
        for att in attachments
        if any(att.lower().endswith(ext)
               for ext in suspicious_extensions)
    ]

    return {
        "attachment_count": len(attachments),
        "suspicious_attachments": suspicious_attachments,
        "suspicious_attachment_count": len(suspicious_attachments)
    }


# Feature 5
def sender_display_name_mismatch(
        sender_name: str,
        sender_domain: str
) -> Dict:
    """
    Detects brand impersonation through display name/domain mismatch.
    """

    if not sender_name or not sender_domain:
        return {
            "mismatch": False,
            "claimed_brand": None,
            "expected_domain": None,
            "actual_domain": sender_domain,
        }

    normalized_name = sender_name.lower().strip()
    normalized_domain = sender_domain.lower().strip()

    for brand, info in KNOWN_BRANDS.items():

        if any(
            keyword in normalized_name
            for keyword in info["keywords"]
        ):

            expected_domain = info["domain"]

            mismatch = not (
                normalized_domain == expected_domain
                or normalized_domain.endswith("." + expected_domain)
            )

            return {
                "mismatch": mismatch,
                "claimed_brand": brand,
                "expected_domain": expected_domain,
                "actual_domain": normalized_domain,
            }

    return {
        "mismatch": False,
        "claimed_brand": None,
        "expected_domain": None,
        "actual_domain": normalized_domain,
    }


# Feature 6
URL_LIKE_PATTERN = re.compile(
    r"(https?://|www\.)[\w\-.]+",
    re.IGNORECASE
)


def check_hidden_links(parsed_email: dict) -> dict:
    """
    Detects visible URLs that redirect to different domains.
    """

    body_html = parsed_email.get("body_html", "")

    if not body_html:
        return {
            "has_hidden_link_mismatch": False,
            "mismatched_links": []
        }

    soup = BeautifulSoup(body_html, "html.parser")

    mismatched_links = []

    for a_tag in soup.find_all("a", href=True):

        href = a_tag["href"].strip()
        visible_text = a_tag.get_text().strip()

        if not visible_text:
            continue

        if URL_LIKE_PATTERN.search(visible_text):

            visible_domain = re.sub(
                r"^https?://",
                "",
                visible_text,
                flags=re.IGNORECASE
            ).split("/")[0].lower()

            href_domain = re.sub(
                r"^https?://",
                "",
                href,
                flags=re.IGNORECASE
            ).split("/")[0].lower()

            if visible_domain != href_domain:
                mismatched_links.append({
                    "visible_text": visible_text,
                    "actual_href": href
                })

    return {
        "has_hidden_link_mismatch": len(mismatched_links) > 0,
        "mismatched_links": mismatched_links
    }


# Observation extraction
def extract_observations(parsed_email: dict) -> dict:
    """
    Runs all feature checks and creates the observation object
    passed to the ReAct agent.
    """

    urgency = calculate_urgency_score(parsed_email)

    headers = parsed_email.get("headers", {})

    reply_mismatch = reply_to_mismatch(
        headers.get("From"),
        headers.get("Reply-To")
    )

    links = check_links(parsed_email)

    attachments = check_attachments(parsed_email)

    display_name_check = sender_display_name_mismatch(
        parsed_email.get("sender_name"),
        parsed_email.get("domain")
    )

    hidden_links = check_hidden_links(parsed_email)

    return {

        # urgency
        "urgency_score": urgency["urgency_score"],
        "matched_urgency_phrases": urgency["matched_phrases"],

        # sender checks
        "reply_to_mismatch": reply_mismatch,
        "display_name_mismatch": display_name_check["mismatch"],
        "claimed_brand": display_name_check["claimed_brand"],

        # links
        "link_count": links["link_count"],
        "all_links_https": links["all_links_https"],
        "hidden_link_mismatch": hidden_links["has_hidden_link_mismatch"],
        "mismatched_links": hidden_links["mismatched_links"],

        # attachments
        "attachment_count": attachments["attachment_count"],
        "suspicious_attachment_count": attachments["suspicious_attachment_count"],
        "suspicious_attachments": attachments["suspicious_attachments"],
    }