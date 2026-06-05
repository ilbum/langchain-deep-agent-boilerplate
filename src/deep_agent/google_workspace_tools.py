"""Google Workspace tools using the Drive and Docs REST APIs directly.

These tools bypass the Google Drive MCP server (drivemcp.googleapis.com), which is in
limited preview and not broadly available, in favour of the stable v1 REST APIs.

Auth: standard OAuth 2.0 refresh token via GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
      GOOGLE_REFRESH_TOKEN. Scope: https://www.googleapis.com/auth/drive.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.tools import tool


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


@tool
def create_google_doc(title: str, content: str) -> str:
    """Create a new Google Doc with the given title and plain-text content.

    Args:
        title: The document title shown in Google Drive.
        content: The body text to insert (plain text; Markdown formatting is preserved as-is).

    Returns:
        The URL of the newly created Google Doc.
    """
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
