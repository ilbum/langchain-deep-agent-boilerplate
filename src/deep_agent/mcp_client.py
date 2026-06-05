"""MCP client lifecycle management.

Exposes load_workspace_tools() — call it explicitly at startup to connect to
Google Workspace MCP servers and retrieve the tool list. No network I/O happens
at import time.

Google Workspace MCP endpoints (one per service):
  Drive:    https://drivemcp.googleapis.com/mcp/v1
  Gmail:    https://gmailmcp.googleapis.com/mcp/v1
  Calendar: https://calendarmcp.googleapis.com/mcp/v1
  Chat:     https://chatmcp.googleapis.com/mcp/v1
  People:   https://people.googleapis.com/mcp/v1

Auth: standard OAuth 2.0 Bearer token obtained by exchanging the refresh token.
"""

import asyncio
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from langchain_mcp_adapters.client import MultiServerMCPClient


def _credentials_configured() -> bool:
    return all(os.environ.get(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"))


def _get_access_token() -> str:
    """Exchange the refresh token for a short-lived access token."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/drive",
        ],
    )
    creds.refresh(Request())
    return creds.token


def _build_mcp_config(access_token: str) -> dict:
    auth_header = {"Authorization": f"Bearer {access_token}"}
    return {
        "google-drive": {
            "url": "https://drivemcp.googleapis.com/mcp/v1",
            "transport": "streamable_http",
            "headers": auth_header,
        },
    }


async def _load_tools() -> list:
    if not _credentials_configured():
        print("WARNING: Google Workspace MCP credentials not set — report-writer subagent will have no tools.")
        return []
    try:
        access_token = _get_access_token()
        client = MultiServerMCPClient(_build_mcp_config(access_token))
        return await client.get_tools()
    except Exception as e:
        print(f"WARNING: Could not connect to Google Workspace MCP server: {e}")
        return []


def load_workspace_tools() -> list:
    """Connect to Google Workspace MCP and return the tool list.

    Returns [] with a warning if credentials are missing or the server is unreachable.
    """
    return asyncio.run(_load_tools())
