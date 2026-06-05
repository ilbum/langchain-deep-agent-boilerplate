"""Google Workspace document adapter.

Auth: standard OAuth 2.0 refresh token via GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
      GOOGLE_REFRESH_TOKEN. Scope: https://www.googleapis.com/auth/drive.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from deep_agent.tools.document.base import DocumentAdapter

_cached_creds: Credentials | None = None


def _get_credentials() -> Credentials:
    global _cached_creds
    if _cached_creds and _cached_creds.valid:
        return _cached_creds
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    creds.refresh(Request())
    _cached_creds = creds
    return creds


def _create_google_doc(title: str, content: str) -> str:
    creds = _get_credentials()
    docs = build("docs", "v1", credentials=creds)

    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": content,
                    }
                }
            ]
        },
    ).execute()

    return f"https://docs.google.com/document/d/{doc_id}/edit"


google_doc = DocumentAdapter(
    name="google_doc",
    description="Create a new Google Doc with a title and plain-text content, returning its URL.",
    fn=_create_google_doc,
)

ADAPTERS: dict[str, DocumentAdapter] = {google_doc.name: google_doc}
