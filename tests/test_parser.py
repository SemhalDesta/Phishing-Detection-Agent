import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from email_ingest.parser import parse_raw_email

SAMPLE_EMAIL = b"""From: "Amazon Support" <amazon-support@amaz0n-login.xyz>
Subject: Urgent Action Required
Reply-To: scammer@different-domain.com
Content-Type: text/html

<html><body>Click <a href="http://amaz0n-login.xyz/verify">here</a> immediately.</body></html>
"""


def test_parse_raw_email_extracts_sender_and_domain():
    parsed = parse_raw_email(SAMPLE_EMAIL, message_id="test-001")
    assert parsed["sender_email"] == "amazon-support@amaz0n-login.xyz"
    assert parsed["domain"] == "amaz0n-login.xyz"


def test_parse_raw_email_extracts_links():
    parsed = parse_raw_email(SAMPLE_EMAIL, message_id="test-002")
    assert "http://amaz0n-login.xyz/verify" in parsed["links"]


def test_parse_raw_email_extracts_reply_to():
    parsed = parse_raw_email(SAMPLE_EMAIL, message_id="test-003")
    assert parsed["headers"].get("Reply-To") == "scammer@different-domain.com"