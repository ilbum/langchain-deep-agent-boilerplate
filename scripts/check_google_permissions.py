#!/usr/bin/env python3
"""Sanity-check script for Google API credentials and permissions.

Run with:
    uv run scripts/check_google_permissions.py

Each check prints PASS / FAIL with a clear message so you know exactly
which GCP APIs still need to be enabled.
"""

import os
import sys
import urllib.request
import json

from dotenv import load_dotenv

load_dotenv()


def section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print("─" * 50)


def ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def fail(msg: str, hint: str = "") -> None:
    print(f"  ✗  {msg}")
    if hint:
        print(f"     → {hint}")


# ── 1. Env vars ────────────────────────────────────────────────────────────────
section("1. Environment variables")

required = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    fail(f"Missing: {', '.join(missing)}", "Add them to .env and re-run.")
    sys.exit(1)
else:
    ok("GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN all set")


# ── 2. Token exchange ──────────────────────────────────────────────────────────
section("2. OAuth token exchange (refresh → access token)")

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    creds.refresh(Request())
    ACCESS_TOKEN = creds.token
    ok(f"Access token obtained (first 20 chars: {ACCESS_TOKEN[:20]}…)")
except Exception as e:
    fail(f"Token exchange failed: {e}", "Check CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN.")
    sys.exit(1)


# ── 3. Token scopes ────────────────────────────────────────────────────────────
section("3. Granted OAuth scopes (via tokeninfo)")

try:
    url = f"https://oauth2.googleapis.com/tokeninfo?access_token={ACCESS_TOKEN}"
    with urllib.request.urlopen(url) as resp:
        info = json.loads(resp.read())
    granted = info.get("scope", "")
    ok(f"Scopes: {granted}")
    if "https://www.googleapis.com/auth/drive" not in granted:
        fail("drive scope missing", "Re-run get_refresh_token.py with the drive scope.")
except Exception as e:
    fail(f"tokeninfo call failed: {e}")


# ── 4. Drive REST API ──────────────────────────────────────────────────────────
section("4. Google Drive REST API (drive.googleapis.com)")

try:
    req = urllib.request.Request(
        "https://www.googleapis.com/drive/v3/about?fields=user",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    ok(f"Drive API OK — authenticated as {data['user']['emailAddress']}")
except Exception as e:
    fail(f"Drive API failed: {e}", "Enable 'Google Drive API' in GCP Console → APIs & Services.")


# ── 5. Docs REST API ──────────────────────────────────────────────────────────
section("5. Google Docs REST API (docs.googleapis.com)")

try:
    from googleapiclient.discovery import build
    docs = build("docs", "v1", credentials=creds)
    doc = docs.documents().create(body={"title": "[permission-check] delete me"}).execute()
    doc_id = doc["documentId"]
    ok(f"Docs API OK — test doc created: https://docs.google.com/document/d/{doc_id}/edit")

    # Clean up: trash the test doc via Drive API
    try:
        drive = build("drive", "v3", credentials=creds)
        drive.files().delete(fileId=doc_id).execute()
        ok("Test doc deleted (clean up complete)")
    except Exception:
        print(f"     ℹ  Could not auto-delete — remove it manually from Drive.")
except Exception as e:
    fail(
        f"Docs API failed: {e}",
        "Enable 'Google Docs API' in GCP Console → APIs & Services → project 697324471467.",
    )


# ── 6. Drive MCP server (optional) ────────────────────────────────────────────
section("6. Google Drive MCP server (drivemcp.googleapis.com) — optional")

try:
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
    }).encode()
    req = urllib.request.Request(
        "https://drivemcp.googleapis.com/mcp/v1",
        data=payload,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if "result" in data and "tools" in data["result"]:
        tools = [t["name"] for t in data["result"]["tools"]]
        ok(f"Drive MCP reachable — tools: {', '.join(tools)}")
    else:
        fail("Drive MCP reachable but returned unexpected response", str(data)[:200])
except Exception as e:
    fail(
        f"Drive MCP unavailable: {e}",
        "This is expected — the API is in limited preview. REST APIs are used instead.",
    )

print(f"\n{'─' * 50}")
print("  Done.")
print("─" * 50)
