DECISION_TO_LABEL = {
    "safe": None,               # leave in inbox, no action
    "suspicious": "REVIEW",
    "phishing": "QUARANTINE",
}

def get_or_create_label_id(service, label_name: str) -> str:
    """Returns the ID of a Gmail label, creating it first if it doesn't exist."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    created_label = service.users().labels().create(
        userId="me", body={"name": label_name}
    ).execute()
    return created_label["id"]


def apply_decision(service, message_id: str, decision: str, confidence: float) -> str:
    """Moves the email based on classification AND confidence. low-confidence
    phishing calls get routed to review"""
    decision_key = decision.lower()

    if decision_key == "safe":
        return "No action taken (classified safe)."

    if decision_key == "phishing" and confidence >= 85:
        label_name = "QUARANTINE"
    else:
        # suspicious, OR phishing-but-low-confidence -- stay visible for review
        label_name = "REVIEW"

    label_id = get_or_create_label_id(service, label_name)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
    ).execute()

    return f"Moved message to {label_name} (confidence: {confidence})."