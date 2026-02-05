"""Lightweight HTTP wrapper for notso-glb CLI.

Exposes notso-glb as an HTTP service for use with Cloudflare Containers/Workflows.
Accepts file uploads, runs the optimizer, and returns the result.

No external dependencies beyond the Python standard library.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

PORT: int = int(os.environ.get("PORT", "8080"))
MAX_UPLOAD_SIZE: int = int(
    os.environ.get("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024))
)  # 100 MB

_TRUTHY: frozenset[str] = frozenset({"true", "1", "yes", "on"})
_FALSY: frozenset[str] = frozenset({"false", "0", "no", "off"})
_ALLOWED_BOOL_VALUES: frozenset[str] = _TRUTHY | _FALSY
_ALLOWED_FORMATS: frozenset[str] = frozenset({"glb", "gltf", "gltf-embedded"})
_PRINTABLE_ASCII_RE: re.Pattern[str] = re.compile(r"[^\x20-\x7E]")
_SAFE_FILENAME_RE: re.Pattern[str] = re.compile(r"[^a-zA-Z0-9._-]")


def parse_multipart(content_type: str, body: bytes) -> dict[str, bytes | str]:
    """Parse a multipart/form-data request body.

    Args:
        content_type: The Content-Type header value including the boundary parameter.
        body: Raw request body bytes.

    Returns:
        A dict mapping field names to their values. File fields have ``bytes``
        values, text fields have ``str`` values. The special key ``_filename``
        stores the uploaded file's original name when present.
    """
    # Extract boundary from Content-Type header
    boundary = ""
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary=") :].strip()
            # Strip optional quotes per RFC 2046
            if (
                len(boundary) >= 2
                and boundary[0] == boundary[-1]
                and boundary[0] in ('"', "'")
            ):
                boundary = boundary[1:-1]
            break
    if not boundary:
        raise ValueError("Missing multipart boundary")

    delimiter = f"--{boundary}".encode()
    parts = body.split(delimiter)
    result: dict[str, bytes | str] = {}

    for part in parts:
        # Skip preamble, epilogue, and closing delimiter
        if not part or part.strip() == b"--" or part.strip() == b"":
            continue

        # Split headers from body at the double CRLF
        if b"\r\n\r\n" in part:
            header_section, part_body = part.split(b"\r\n\r\n", 1)
        elif b"\n\n" in part:
            header_section, part_body = part.split(b"\n\n", 1)
        else:
            continue

        # Strip trailing \r\n from body
        if part_body.endswith(b"\r\n"):
            part_body = part_body[:-2]

        headers_text = header_section.decode("utf-8", errors="replace")
        name = None
        filename = None
        for line in headers_text.split("\n"):
            line = line.strip()
            if line.lower().startswith("content-disposition:"):
                for token in line.split(";"):
                    token = token.strip()
                    if token.startswith("name="):
                        name = token[len("name=") :].strip('"')
                    elif token.startswith("filename="):
                        filename = token[len("filename=") :].strip('"')

        if name is None:
            continue

        if filename is not None:
            result[name] = part_body
            result["_filename"] = filename
        else:
            result[name] = part_body.decode("utf-8", errors="replace")

    return result


# Options that map to CLI boolean flags (--flag/--no-flag)
BOOL_FLAGS: dict[str, tuple[str, str]] = {
    "draco": ("--draco", "--no-draco"),
    "webp": ("--webp", "--no-webp"),
    "gltfpack": ("--gltfpack", "--no-gltfpack"),
    "analyze_animations": ("--analyze-animations", "--skip-animation-analysis"),
    "check_bloat": ("--check-bloat", "--skip-bloat-check"),
    "autofix": ("--autofix", "--stable"),
    "force_pot": ("--force-pot", ""),
}

# Options that take a value
VALUE_OPTIONS: dict[str, str] = {
    "format": "--format",
    "max_texture_size": "--max-texture-size",
}


def build_cli_args(params: dict[str, str]) -> list[str]:
    """Convert request parameters to validated notso-glb CLI arguments.

    Args:
        params: Mapping of parameter names to their string values
            (e.g. ``{"draco": "true", "max_texture_size": "512"}``).

    Returns:
        A list of CLI flag strings ready to be passed to the notso-glb command.

    Raises:
        ValueError: If any parameter value fails validation (unknown boolean
            value, non-integer texture size, unrecognised output format, etc.).
    """
    args: list[str] = []

    for key, (on_flag, off_flag) in BOOL_FLAGS.items():
        if key in params:
            val = params[key].lower()
            if val not in _ALLOWED_BOOL_VALUES:
                raise ValueError(
                    f"Invalid value for '{key}': '{params[key]}'. "
                    f"Expected one of: {', '.join(sorted(_ALLOWED_BOOL_VALUES))}"
                )
            if val in _TRUTHY:
                args.append(on_flag)
            elif off_flag:
                args.append(off_flag)

    if "format" in params:
        fmt = params["format"]
        if fmt not in _ALLOWED_FORMATS:
            raise ValueError(
                f"Invalid format: '{fmt}'. "
                f"Expected one of: {', '.join(sorted(_ALLOWED_FORMATS))}"
            )
        args.extend(["--format", fmt])

    if "max_texture_size" in params:
        raw = params["max_texture_size"]
        try:
            size = int(raw)
        except ValueError:
            raise ValueError(
                f"Invalid max_texture_size: '{raw}'. Expected an integer."
            ) from None
        if size < 0 or size > 16384:
            raise ValueError(
                f"max_texture_size out of range: {size}. Expected 0-16384."
            )
        args.extend(["--max-texture-size", str(size)])

    return args


def parse_query_string(qs: str) -> dict[str, str]:
    """Parse a URL query string into a dict with proper percent-decoding.

    Args:
        qs: Raw query string (everything after the ``?``), e.g.
            ``"draco=true&max_texture_size=512"``.

    Returns:
        A dict mapping decoded parameter names to decoded values.
        When duplicate keys exist the last value wins.
    """
    return dict(urllib.parse.parse_qsl(qs, keep_blank_values=True))


class OptimizeHandler(BaseHTTPRequestHandler):
    """HTTP request handler that wraps the notso-glb CLI."""

    def log_message(self, fmt: str, *args: object) -> None:
        """Log a formatted message to stdout for container log collection.

        Args:
            fmt: A percent-style format string (e.g. ``"Running: %s"``).
            *args: Values substituted into *fmt* via ``%`` formatting.

        Returns:
            None.
        """
        print(f"[server] {fmt % args}")

    def do_GET(self) -> None:
        """Handle GET requests for health checks and service info."""
        path = self.path.split("?")[0]

        if path == "/health":
            self._respond_json(HTTPStatus.OK, {"status": "healthy"})
            return

        if path == "/":
            self._respond_json(
                HTTPStatus.OK,
                {
                    "service": "notso-glb",
                    "endpoints": {
                        "POST /optimize": "Upload a 3D file for optimization",
                        "GET /health": "Health check",
                    },
                    "parameters": {
                        "format": "glb | gltf | gltf-embedded (default: glb)",
                        "draco": "true | false (default: true)",
                        "webp": "true | false (default: true)",
                        "gltfpack": "true | false (default: true)",
                        "max_texture_size": "int pixels (default: 1024, 0=no resize)",
                        "force_pot": "true | false (default: false)",
                        "analyze_animations": "true | false (default: true)",
                        "check_bloat": "true | false (default: true)",
                        "autofix": "true | false (default: false)",
                    },
                },
            )
            return

        self._respond_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        """Handle POST requests for file optimization."""
        path = self.path.split("?")[0]

        if path != "/optimize":
            self._respond_json(
                HTTPStatus.NOT_FOUND, {"error": "Not found. Use POST /optimize"}
            )
            return

        content_type_raw: str = self.headers.get("Content-Type", "")
        content_type: str = content_type_raw.lower()
        try:
            content_length: int = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            self._respond_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Invalid Content-Length header"},
            )
            return

        if content_length <= 0:
            self._respond_json(
                HTTPStatus.BAD_REQUEST, {"error": "Invalid Content-Length header"}
            )
            return

        if content_length > MAX_UPLOAD_SIZE:
            self._respond_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {
                    "error": f"Upload exceeds maximum size "
                    f"({MAX_UPLOAD_SIZE // (1024 * 1024)} MB)"
                },
            )
            return

        body: bytes = self.rfile.read(content_length)

        # Collect parameters from query string
        query_params: dict[str, str] = {}
        if "?" in self.path:
            query_params = parse_query_string(self.path.split("?", 1)[1])

        # Handle multipart/form-data (file upload with optional params)
        if "multipart/form-data" in content_type:
            try:
                parts = parse_multipart(content_type_raw, body)
            except ValueError as e:
                self._respond_json(
                    HTTPStatus.BAD_REQUEST, {"error": f"Invalid multipart: {e}"}
                )
                return

            file_data = parts.get("file")
            if not isinstance(file_data, bytes):
                self._respond_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Missing 'file' field in multipart upload"},
                )
                return

            raw_mp_name: str = str(parts.get("_filename", "input.glb"))
            filename: str = _SAFE_FILENAME_RE.sub("_", os.path.basename(raw_mp_name))
            if not filename:
                filename = "input.glb"

            # Merge form text fields into params (query string takes precedence)
            for k, v in parts.items():
                if k not in ("file", "_filename") and isinstance(v, str):
                    query_params.setdefault(k, v)

        # Handle application/octet-stream (raw binary upload)
        elif "application/octet-stream" in content_type:
            file_data = body
            # Sanitize X-Filename: strip to basename, replace unsafe chars
            raw_filename: str = self.headers.get("X-Filename", "input.glb")
            filename = _SAFE_FILENAME_RE.sub("_", os.path.basename(raw_filename))
            if not filename:
                filename = "input.glb"

        else:
            self._respond_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {
                    "error": "Unsupported Content-Type. "
                    "Use multipart/form-data or application/octet-stream"
                },
            )
            return

        self._process_file(file_data, filename, query_params)

    def _process_file(
        self,
        file_data: bytes,
        filename: str,
        params: dict[str, str],
    ) -> None:
        """Write the uploaded file to a temp dir, run notso-glb, return result."""
        work_dir = tempfile.mkdtemp(prefix="notso-glb-")
        try:
            # Sanitize filename: keep only the basename, reject path traversal
            safe_name = os.path.basename(filename)
            if not safe_name:
                safe_name = "input.glb"
            input_path = os.path.normpath(os.path.join(work_dir, safe_name))
            if not input_path.startswith(work_dir + os.sep):
                self._respond_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Invalid filename (path traversal rejected)"},
                )
                return

            with open(input_path, "wb") as f:
                f.write(file_data)

            # Determine output format extension
            fmt = params.get("format", "glb")
            out_ext = ".gltf" if fmt.startswith("gltf") else ".glb"
            output_name = f"output_{uuid.uuid4().hex[:8]}{out_ext}"
            output_path = os.path.join(work_dir, output_name)

            # Build and validate CLI arguments
            try:
                extra_args = build_cli_args(params)
            except ValueError as e:
                self._respond_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": f"Invalid parameter: {e}"},
                )
                return

            cmd = [
                "notso-glb",
                *extra_args,
                "--quiet",
                "-o",
                output_path,
                "--",
                input_path,
            ]

            self.log_message("Running: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=work_dir,
            )

            if result.returncode != 0:
                stderr = result.stderr or result.stdout or "Unknown error"
                print(f"[ERROR] notso-glb failed: {stderr}")
                self._respond_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": "Optimization failed",
                        "details": stderr[-2000:],  # Limit error output
                    },
                )
                return

            if not os.path.isfile(output_path):
                self._respond_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "Output file was not created"},
                )
                return

            # Read and return the optimized file
            with open(output_path, "rb") as f:
                output_data = f.read()

            content_type = (
                "model/gltf-binary" if out_ext == ".glb" else "model/gltf+json"
            )

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(output_data)))
            self.send_header(
                "Content-Disposition", f'attachment; filename="{output_name}"'
            )
            # Include stdout logs as a header for debugging
            if result.stdout:
                # Sanitize to printable ASCII only (\x20-\x7E), then truncate
                log_summary = _PRINTABLE_ASCII_RE.sub(" ", result.stdout)[:500].strip()
                if log_summary:
                    self.send_header("X-Optimization-Log", log_summary)
            self.end_headers()
            self.wfile.write(output_data)

        except subprocess.TimeoutExpired:
            print("[ERROR] notso-glb timed out after 300s")
            self._respond_json(
                HTTPStatus.GATEWAY_TIMEOUT,
                {"error": "Optimization timed out (5 minute limit)"},
            )
        except subprocess.SubprocessError as e:
            print(f"[ERROR] Subprocess error: {e}")
            self._respond_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Subprocess error: {e}"},
            )
        except OSError as e:
            print(f"[ERROR] I/O error: {e}")
            self._respond_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"I/O error: {e}"},
            )
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _respond_json(self, status: HTTPStatus, data: dict[str, object]) -> None:
        """Send a JSON response."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    """Start the HTTP server and block until interrupted.

    Reads ``PORT`` from the environment (default 8080). Uses a threading server
    so that long-running ``/optimize`` requests do not block ``/health`` checks.
    """
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OptimizeHandler)
    print(f"[server] notso-glb HTTP wrapper listening on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Shutting down")
    server.server_close()


if __name__ == "__main__":
    main()
