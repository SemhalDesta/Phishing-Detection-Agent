import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from email_ingest.features import extract_observations
from tools.header_check import check_spf_dkim


def make_parsed_email(**overrides) -> dict:
    base = {
        "message_id": "test",
        "sender_name": "Amazon Support",
        "sender_email": "amazon-support@amaz0n-login.xyz",
        "domain": "amaz0n-login.xyz",
        "subject": "Urgent Action Required",
        "body_plain": "Click below immediately to verify your account.",
        "body_html": "",
        "links": ["http://amaz0n-login.xyz/verify"],
        "attachments": [],
        "headers": {},
    }
    base.update(overrides)
    return base


def test_urgency_score_detects_keywords():
    parsed = make_parsed_email()
    obs = extract_observations(parsed)
    assert obs["urgency_score"] > 0
    assert "urgent" in obs["matched_urgency_phrases"] or "immediately" in obs["matched_urgency_phrases"]


def test_reply_to_mismatch_detected():
    parsed = make_parsed_email(headers={"From": "amazon-support@amaz0n-login.xyz",
                                         "Reply-To": "scammer@different-domain.com"})
    obs = extract_observations(parsed)
    assert obs["reply_to_mismatch"] is True


def test_suspicious_attachment_flagged():
    parsed = make_parsed_email(attachments=["invoice.exe"])
    obs = extract_observations(parsed)
    assert obs["suspicious_attachment_count"] == 1


def test_check_spf_dkim_parses_pass():
    header = "spf=pass smtp.mailfrom=amazon.com; dkim=pass header.d=amazon.com"
    result = check_spf_dkim.invoke({"authentication_results_header": header})
    assert "SPF: pass" in result
    assert "DKIM: pass" in result