import pandas as pd
from email.message import EmailMessage
from pathlib import Path

def build_eval_dataset(csv_path: str, output_dir: str, n_per_class: int = 30):
    """Samples n_per_class phishing and n_per_class legitimate emails from
    the dataset, writes each as a .eml file, and returns a labels list."""
    df = pd.read_csv(csv_path)

    legit_sample = df[df["label"] == 0].sample(n=n_per_class, random_state=42)
    phishing_sample = df[df["label"] == 1].sample(n=n_per_class, random_state=42)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    records = []

    for i, (_, row) in enumerate(legit_sample.iterrows()):
        filename = f"legit_{i:04d}.eml"
        _write_eml(output_path / filename, row)
        records.append({"filename": filename, "label": "safe"})

    for i, (_, row) in enumerate(phishing_sample.iterrows()):
        filename = f"phish_{i:04d}.eml"
        _write_eml(output_path / filename, row)
        records.append({"filename": filename, "label": "phishing"})

    labels_df = pd.DataFrame(records)
    labels_df.to_csv(output_path.parent / "labels.csv", index=False)

    return records


def _sanitize_header_value(value: str) -> str:
    """Removes newline/carriage-return characters so a value can be safely
    used as an email header -- some rows in the raw dataset have messy,
    multi-line sender/subject fields."""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _write_eml(filepath, row) -> None:
    """Builds a minimal raw email from CSV columns and writes it as .eml bytes."""
    msg = EmailMessage()
    msg["From"] = _sanitize_header_value(row.get("sender", "unknown@example.com"))
    msg["Subject"] = _sanitize_header_value(row.get("subject", ""))
    msg.set_content(str(row.get("body", "")))

    with open(filepath, "wb") as f:
        f.write(msg.as_bytes())


if __name__ == "__main__":
    records = build_eval_dataset(
        csv_path = "Nazario_5.csv",
        output_dir="evaluation/dataset/emails",
        n_per_class=30,
    )
    print(f"Wrote {len(records)} .eml files and labels.csv")