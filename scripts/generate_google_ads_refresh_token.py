"""Generate a local Google Ads OAuth refresh token without printing secrets."""

from __future__ import annotations

import argparse
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from requests_oauthlib import OAuth2Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCOPE = "https://www.googleapis.com/auth/adwords"
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Desktop OAuth redirects back to a local loopback server, which is safe here.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    authorization_response: str | None = None
    callback_event = threading.Event()

    def do_GET(self) -> None:  # noqa: N802 - HTTP handler method name
        OAuthCallbackHandler.authorization_response = (
            f"http://{self.headers['Host']}{self.path}"
        )
        OAuthCallbackHandler.callback_event.set()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<h1>Authorization complete</h1><p>You can close this tab and return to the terminal.</p>"
        )

    def log_message(self, format: str, *args: object) -> None:
        # OAuth query strings can contain authorization codes; do not log them.
        return


def load_desktop_credentials(path: Path) -> tuple[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    credentials = payload.get("installed", {})
    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")
    if not client_id or not client_secret:
        raise ValueError("Expected a Desktop app OAuth JSON containing installed credentials.")
    return client_id, client_secret


def update_env_value(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    replacement = f"{key}={value}"
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--oauth-client-json",
        type=Path,
        required=True,
        help="Path to the downloaded Desktop app OAuth client JSON.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    client_id, client_secret = load_desktop_credentials(args.oauth_client_json)
    server = HTTPServer(("127.0.0.1", 0), OAuthCallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth2callback"
    session = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=[DEFAULT_SCOPE])
    authorization_url, _ = session.authorization_url(
        AUTHORIZATION_URL,
        access_type="offline",
        prompt="consent",
    )

    print("Opening Google authorization in your browser. Sign in with the Google Ads account owner.")
    webbrowser.open(authorization_url)
    server.timeout = 1
    elapsed = 0
    while not OAuthCallbackHandler.callback_event.is_set() and elapsed < args.timeout_seconds:
        server.handle_request()
        elapsed += 1
    server.server_close()

    if not OAuthCallbackHandler.authorization_response:
        raise TimeoutError("No OAuth callback was received before the timeout.")

    callback_query = urlparse(OAuthCallbackHandler.authorization_response).query
    if "error=" in callback_query:
        raise RuntimeError("Google denied the OAuth request. Check the test-user and scope settings.")

    token = session.fetch_token(
        TOKEN_URL,
        authorization_response=OAuthCallbackHandler.authorization_response,
        client_secret=client_secret,
    )
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("No refresh token returned. Re-run and approve the consent request.")

    update_env_value(PROJECT_ROOT / ".env", "GOOGLE_ADS_REFRESH_TOKEN", refresh_token)
    print("Refresh token saved locally to .env. No secret values were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
