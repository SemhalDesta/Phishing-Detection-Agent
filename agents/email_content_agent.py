"""
Agent 1: Email Content Agent.
Analyzes sender, subject, urgency, attachments, and wording. No external
tools. Always runs first, on every email.
"""
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from config import GOOGLE_API_KEY, LLM_MODEL
from email_ingest.features import extract_observations


class EmailContentAssessment(BaseModel):
    risk_score: int = Field(description="0-100 risk score based on content signals alone")
    reasoning: str = Field(description="1-3 sentence explanation of the score")
    flags: list[str] = Field(
        default_factory=list,
        description="Specific concerning signals found, e.g. 'urgency_language', "
                    "'display_name_mismatch', 'suspicious_attachment'"
    )


CONTENT_AGENT_PROMPT = """You are the Email Content Agent in a multi-agent phishing \
detection system. Your job is to assess phishing risk using ONLY the email's \
content and structure -- you have no access to external tools (no domain \
lookups, no reputation checks). Another agent handles that separately.

Analyze the observations and body content below and produce a risk score \
(0-100, where 100 is certainly phishing) with reasoning.

Sender: {sender_email} (display name: "{sender_name}")
Sender domain: {sender_domain}
Subject: {subject}

Observations:
{observations}

Body (truncated):
{body}
"""


def _format_observations(obs: dict) -> str:
    return (
        f"- Urgency score: {obs['urgency_score']} (matched: {obs['matched_urgency_phrases']})\n"
        f"- Reply-To mismatch: {obs['reply_to_mismatch']}\n"
        f"- Display name mismatch: {obs['display_name_mismatch']} (claimed brand: {obs['claimed_brand']})\n"
        f"- Link count: {obs['link_count']} (all HTTPS: {obs['all_links_https']})\n"
        f"- Hidden link mismatch: {obs['hidden_link_mismatch']}\n"
        f"- Attachment count: {obs['attachment_count']} (suspicious: {obs['suspicious_attachment_count']})"
    )


def run_email_content_agent(parsed_email: dict) -> EmailContentAssessment:
    """Runs Agent 1 and returns a structured risk assessment."""
    observations = extract_observations(parsed_email)

    prompt = CONTENT_AGENT_PROMPT.format(
        sender_email=parsed_email["sender_email"],
        sender_name=parsed_email["sender_name"],
        sender_domain=parsed_email["domain"],
        subject=parsed_email["subject"],
        observations=_format_observations(observations),
        body=parsed_email["body_plain"][:500],
    )

    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(EmailContentAssessment)

    return structured_llm.invoke(prompt)