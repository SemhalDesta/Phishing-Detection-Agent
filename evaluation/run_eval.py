"""
Runs the agent over the labeled evaluation dataset and reports precision/
recall/F1. Also logs every email's full reasoning trace to the database,
so tool usage and individual traces can be inspected afterward.
"""
import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import DATABASE_URL
from database.models import get_session
from email_ingest.parser import parse_raw_email
from email_ingest.features import extract_observations, build_email_context
from agent.react_agent import run_agent
from app import log_email_result  # reuse the same logging function app.py uses

DATASET_DIR = Path(__file__).parent / "dataset"
EMAILS_DIR = DATASET_DIR / "emails"
LABELS_FILE = DATASET_DIR / "labels.csv"


def load_labels() -> dict[str, str]:
    labels = {}
    with open(LABELS_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels[row["filename"]] = row["label"].lower()
    return labels


def evaluate():
    labels = load_labels()
    y_true, y_pred = [], []

    session_factory = get_session(DATABASE_URL)
    session = session_factory()

    for filename, true_label in labels.items():
        raw_bytes = (EMAILS_DIR / filename).read_bytes()
        parsed = parse_raw_email(raw_bytes, message_id=filename)

        observations = extract_observations(parsed)
        context = build_email_context(parsed, observations)

        result = run_agent(context)
        predicted_label = result["classification"].lower()

        log_email_result(session, filename, parsed, result)

        y_true.append(true_label)
        y_pred.append(predicted_label)
        print(f"{filename}: true={true_label} predicted={predicted_label} confidence={result['confidence']}")

    session.close()

    print_metrics(y_true, y_pred)
    print_binary_detection_metrics(y_true, y_pred)
   


def print_metrics(y_true: list[str], y_pred: list[str]):
    # Only score classes that actually exist in the ground truth --
    # "suspicious" has no true label to match against, so it doesn't belong here.
    labels = sorted(set(y_true))

    print("\n--- Per-class metrics (ground-truth classes only) ---")
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        print(f"{label}: precision={precision:.2f} recall={recall:.2f} f1={f1:.2f} (n={y_true.count(label)})")

    exact_matches = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    print(f"\nOverall accuracy (exact label match): {exact_matches / len(y_true):.2f}")

    # Report "suspicious" as a rate, broken down by what it was actually uncertain about --
    # not scored as a class, since no ground-truth email is labeled "suspicious"
    suspicious_on_phishing = sum(1 for t, p in zip(y_true, y_pred) if t == "phishing" and p == "suspicious")
    suspicious_on_safe = sum(1 for t, p in zip(y_true, y_pred) if t == "safe" and p == "suspicious")
    print(f"\n'Suspicious' verdicts on truly phishing emails: {suspicious_on_phishing}/{y_true.count('phishing')}")
    print(f"'Suspicious' verdicts on truly safe emails: {suspicious_on_safe}/{y_true.count('safe')}")


def print_binary_detection_metrics(y_true: list[str], y_pred: list[str]):
    """Treats 'suspicious' and 'phishing' both as 'flagged' -- since either
    means the agent didn't silently let the email through as safe. This
    reflects the actual operational outcome: both route the email out of
    the inbox (Review or Quarantine), not just a strict label match."""
    flagged_true = [t == "phishing" for t in y_true]
    flagged_pred = [p in ("phishing", "suspicious") for p in y_pred]

    tp = sum(1 for t, p in zip(flagged_true, flagged_pred) if t and p)
    fp = sum(1 for t, p in zip(flagged_true, flagged_pred) if not t and p)
    fn = sum(1 for t, p in zip(flagged_true, flagged_pred) if t and not p)
    tn = sum(1 for t, p in zip(flagged_true, flagged_pred) if not t and not p)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(y_true)

    print(f"\n--- Binary detection (phishing+suspicious vs safe) ---")
    print(f"precision={precision:.2f} recall={recall:.2f} f1={f1:.2f} accuracy={accuracy:.2f}")
    print(f"(tp={tp}, fp={fp}, fn={fn}, tn={tn})")


if __name__ == "__main__":
    evaluate()