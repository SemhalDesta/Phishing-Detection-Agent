import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from response.actions import get_or_create_label_id


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]# the scope of access the app requires the user. it could be readonly which prevetns the app from modifying anything


#Authenticate the user with Google, create a Gmail API service object, and return it so you can make Gmail API requests.
def get_gmail_services()-> tuple:
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service, creds

def fetch_unread_message_ids(service, max_results=10):
    """Fetches unread inbox messages that the agent hasn't already processed."""
    try:
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX", "UNREAD"],
                q="-label:AGENT_PROCESSED",
                maxResults=max_results,
            )
            .execute()
        )
        messages = results.get("messages", [])
        return [msg["id"] for msg in messages]
    except Exception as e:
        print(f"An error occurred while fetching unread message IDs: {e}")
        return []


def download_raw_message(service, message_id) -> bytes:
    """Downloads and decodes the raw content of a Gmail message by its ID."""
    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="raw")
            .execute()
        )
        raw_message = base64.urlsafe_b64decode(message["raw"].encode("ASCII"))
        return raw_message
    except Exception as e:
        print(f"An error occurred while downloading the message: {e}")
        return None

def mark_as_processed(service, message_id):
    """Tags a message as agent-processed, without touching its read status --
    the human's own read/unread state stays exactly as they left it."""
    try:
        label_id = get_or_create_label_id(service, "AGENT_PROCESSED")
        service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": [label_id]}
        ).execute()
        print(f"Message {message_id} tagged as processed.")
    except Exception as e:
        print(f"An error occurred while tagging the message as processed: {e}")

