import base64
import os
import re
import mimetypes
from pathlib import Path

from flask import Flask, request, jsonify, Response, abort, send_file
from flask_cors import CORS

app = Flask(__name__)

SITES_BASE_DIR = Path(os.environ.get("SITES_BASE_DIR", "/var/www/html/")).resolve()
PUBLIC_HOST = os.environ.get("PUBLIC_HOST", "http://github.com").rstrip("/") + "/"
ENABLE_DEV_CORS = os.environ.get("ENABLE_DEV_CORS", "false").lower() == "true"
ENABLE_FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
APP_DIR = Path(__file__).parent.resolve()

MAX_FILENAME_LENGTH = 80
MAX_FILE_BYTES = 500_000

ALLOWED_EXTENSIONS = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".json",
    ".txt",
    ".md",
    ".svg",
    ".xml",
}

ALLOWED_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")

if ENABLE_DEV_CORS:
    CORS(
        app,
        origins=[
            "null",
            "http://localhost",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
    )


@app.get("/")
def main():
    return send_file(APP_DIR / "index.html")


def get_basic_auth_username() -> str:
    """
    Reads username from Authorization: Basic base64(username:password).

    If Basic Auth is not present, return "" so the app can use the default
    sites folder directly instead of /sites/<username>/.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Basic "):
        return ""

    encoded = auth_header.removeprefix("Basic ").strip()

    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except Exception:
        abort(401, "Invalid Basic Auth header")

    if ":" not in decoded:
        abort(401, "Invalid Basic Auth format")

    username = decoded.split(":", 1)[0]
    return username


def user_root(username: str) -> Path:
    """
    Empty username means use SITES_BASE_DIR itself.
    Otherwise use SITES_BASE_DIR / username.
    """
    root = (SITES_BASE_DIR / username).resolve() if username else SITES_BASE_DIR

    if root != SITES_BASE_DIR and not root.is_relative_to(SITES_BASE_DIR):
        abort(400, "Invalid username path")

    if not root.exists():
        abort(404, f"User folder does not exist: {username}")

    if not root.is_dir():
        abort(400, "User root is not a directory")

    return root


def validate_file_content_size(content: str):
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        abort(413, "File is too large")


def safe_user_file(root: Path, filename: str) -> Path:
    """
    Maps a filename to a safe path inside the user's folder.

    Allows only simple flat filenames with web-safe extensions.
    Rejects nested paths, traversal attempts, hidden files, weird characters,
    very long filenames, and non-web-safe file types.
    """
    filename = (filename or "").strip()

    if not filename:
        abort(400, "Missing filename")

    if len(filename) > MAX_FILENAME_LENGTH:
        abort(400, "Filename is too long")

    if "/" in filename or "\\" in filename:
        abort(400, "Folders are not allowed in filenames")

    if filename in {".", ".."}:
        abort(400, "Invalid filename")

    if filename.startswith("."):
        abort(400, "Hidden files are not allowed")

    if not ALLOWED_FILENAME_RE.match(filename):
        abort(
            400,
            "Filename must use only letters, numbers, dots, hyphens, and underscores",
        )

    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        abort(
            400,
            f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    path = (root / filename).resolve()

    if not path.is_relative_to(root):
        abort(400, "Invalid file path")

    return path


def list_site_files(root: Path) -> list[str]:
    """
    Lists web-safe editable files in the user's folder.
    """
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    )


def response_for_file(path: Path) -> Response:
    """
    Returns file content with a reasonable MIME type.

    Falls back to text/plain for unknown types.
    """
    mime_type, _encoding = mimetypes.guess_type(path.name)

    return Response(
        path.read_text(encoding="utf-8"),
        mimetype=f"{mime_type or 'text/plain'}; charset=utf-8",
    )


@app.get("/api/me")
def me():
    username = get_basic_auth_username()
    root = user_root(username)

    return jsonify(
        {
            "root": username,
            "host": PUBLIC_HOST,
            "files": list_site_files(root),
        }
    )


@app.get("/api/get/<path:page_name>")
def get_page(page_name):
    username = get_basic_auth_username()
    root = user_root(username)
    path = safe_user_file(root, page_name)

    if not path.exists():
        abort(404, "File not found")

    if not path.is_file():
        abort(400, "Not a file")

    return response_for_file(path)


@app.delete("/api/delete/<path:page_name>")
def delete_page(page_name):
    username = get_basic_auth_username()
    root = user_root(username)
    path = safe_user_file(root, page_name)

    if not path.exists():
        abort(404, "File not found")

    if not path.is_file():
        abort(400, "Not a file")

    path.unlink()

    return jsonify(
        {
            "ok": True,
            "deleted": page_name,
        }
    )


@app.post("/api/create/<path:page_name>")
def create_page(page_name):
    username = get_basic_auth_username()
    root = user_root(username)
    path = safe_user_file(root, page_name)

    if path.exists():
        abort(409, "File already exists")

    body = request.get_json(silent=True) or {}

    content = body.get("content") or f"""<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, height=device-height, initial-scale=1">
  </head>
  <body>
    <h1>Your New {page_name} Page</h1>
  </body>
</html>"""

    validate_file_content_size(content)
    path.write_text(content, encoding="utf-8")

    return jsonify(
        {
            "ok": True,
            "created": page_name,
        }
    )


@app.post("/api/rename/<path:old_name>")
def rename_page(old_name):
    username = get_basic_auth_username()
    root = user_root(username)

    body = request.get_json(silent=True) or {}
    new_name = body.get("newName")

    if not new_name:
        abort(400, "Missing newName")

    old_path = safe_user_file(root, old_name)
    new_path = safe_user_file(root, new_name)

    if not old_path.exists():
        abort(404, "Source file not found")

    if not old_path.is_file():
        abort(400, "Source is not a file")

    if new_path.exists():
        abort(409, "Destination file already exists")

    old_path.rename(new_path)

    return jsonify(
        {
            "ok": True,
            "oldName": old_name,
            "newName": new_name,
        }
    )


@app.post("/api/publish/<path:page_name>")
def publish_page(page_name):
    username = get_basic_auth_username()
    root = user_root(username)
    path = safe_user_file(root, page_name)

    content_type = request.headers.get("Content-Type", "")

    if "application/json" in content_type:
        body = request.get_json(silent=True) or {}
        content = body.get("content", "")
    else:
        content = request.get_data(as_text=True)

    validate_file_content_size(content)
    path.write_text(content, encoding="utf-8")

    return jsonify(
        {
            "ok": True,
            "published": page_name,
        }
    )


@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(413)
def handle_error(error):
    return (
        jsonify(
            {
                "ok": False,
                "error": error.description,
            }
        ),
        error.code,
    )


if __name__ == "__main__":
    app.run(debug=ENABLE_FLASK_DEBUG, threaded=True)
