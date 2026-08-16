# ReAct-Based Phishing Email Detection Agent

This is an autonomous phishing Email detection agent that uses ReAct reasoning strategy to identify phishing emails and quarantine them. 
The agent connects to a live Gmail inbox and investigates incoming by continuously polling unopened emails. It goes through the email looking for 
phishing indicators using ReAct (Reasoning + Acting) loop and takes an autonomous action: quarantining high-confidence phihsing detections, 
routing ambiguous cases for a review  and leaving the legitimate emails in the inbox. The agent logs its reasoning steps for each email in a queryable 
database for a review which is also visible in a Streamlit monitoring dashboard which makes it transparent instead of a black box. 

## How it works

1. **Ingestion**: polls Gmail via the Gmail API for new unread inbox mail
2. **Parsing**: extracts the sender, domain, links, attachments, and headers from the raw email content
3. **Feature extraction**: it extracts features such as urgency language, display-name mismatch, link/HTTPS status, hidden-link mismatch, attachment risk, reply-to mismatch  from the email by using the deconstructed components of the email in the previous step.
4. **Reasoning**: a LangGraph-based ReAct loop reasons over these observations and adaptively calls external tools (WHOIS domain age, VirusTotal reputation, SPF/DKIM verification) only when needed
5. **Decision & response**: classifies as Safe or Suspicious or Phishing with a confidence score; confidently-flagged phishing is quarantined, ambiguous cases are routed to review, safe email is left in the inbox
6. **Logging**: every step of the reasoning trace is persisted to SQLite, queryable and viewable via the dashboard

## Setup

1. **Create a virtual environment and install dependencies**
  python -m venv venv
  venv\Scripts\activate # Windows
  source venv/bin/activate # macOS/Linux
  pip install -r requirements.txt

2. **Set up a test Gmail account** 
   - Create a Google Cloud project and enable the Gmail API
   - Create OAuth client credentials (Desktop app type), download as `credentials.json`, place in the project root
   - Keep the OAuth consent screen in **Testing** mode and add your test account under Test users 
   - On first run, a browser window opens for you to authorize; a cached `token.json` is created afterward (expires every 7 days in Testing mode, just re-authorize when it does)

3. **Copy `.env.example` to `.env`** and fill in:
   - `ANTHROPIC_API_KEY`: from console.anthropic.com
   - `VIRUSTOTAL_API_KEY`: free tier at virustotal.com/gui/join-us
   - `LLM_MODEL`: defaults to Claude Sonnet if unset; can be swapped to a cheaper model (e.g. Haiku) for development. But the accuracy of each model decreases with the price.

4. **Run the live agent**
   python app.py or py app.py
   Polls the inbox every 30 seconds by default (`POLL_INTERVAL_SECONDS` in `.env`). Send yourself a test email and watch it get classified, labeled in Gmail, and logged automatically.

5. **View the monitoring dashboard**
   streamlit run frontend/dashboard.py
   (or `py -m streamlit run frontend/dashboard.py` if `streamlit` isn't recognized directly on your system PATH)

   Shows every processed email with its decision and confidence, and lets you expand any email to see its full step-by-step reasoning trace, including exactly which tools were called and what they returned.

6. **Run tests**
   pytest tests/
   
## Evaluation

## Evaluation

The agent was evaluated on a 90-email labeled dataset: 30 legitimate emails were taken from the Enron
corpus, and 60 phishing emails split evenly between the historical Nazario
corpus (30) and recently-collected Phishing Pot samples (30) which addresses
the temporal mismatch between static training corpora and real-time
verification tools by including both older and current phishing samples.

**Final results (using Claude Sonnet AI model):**

| Metric | Phishing (strict) | Safe (strict) | Binary detection (phishing+suspicious vs safe) |
|---|---|---|---|
| Precision | 1.00 | 0.86 | 1.00 |
| Recall | 0.62 | 1.00 | 0.92 |
| F1 | 0.76 | 0.92 | 0.96 |
| Accuracy | 0.74 (overall exact match) | — | 0.94 |
| n | 60 | 30 | 90 |

Confusion matrix (binary detection): tp=55, fp=0, fn=5, tn=30.

"Suspicious" verdicts are reported separately rather than scored as a third
class, since no email in the dataset is ground-truth labeled "suspicious" —
18 of 60 phishing emails were flagged suspicious rather than confidently
classified either way, reflecting calibrated caution rather than
misclassification (0 of 30 safe emails were ever flagged suspicious). See
`evaluation/run_eval.py` for full metric methodology.

## Known limitations

- Historical dataset samples (Nazario) reflect present-day WHOIS/VirusTotal status, not attack-time status
- Repeated evaluation runs on identical inputs can produce different verdicts on borderline cases, reflecting the non-deterministic nature of LLM-based reasoning
- The tool-calling decision is made by the LLM's own judgment, not a fixed confidence threshold
