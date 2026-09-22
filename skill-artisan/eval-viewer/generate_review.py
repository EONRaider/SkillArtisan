#!/usr/bin/env python3
"""Generate and serve a review page for eval results.

Ported unchanged from skill-creator's eval-viewer/generate_review.py (row 15,
Stage 1) — this is a concrete, working artifact worth porting faithfully, not
reinventing. Reads the workspace directory, discovers runs (directories with
outputs/), embeds all output data into a self-contained HTML page (viewer.html,
Outputs + Benchmark tabs), and serves it via a tiny HTTP server. Feedback
auto-saves to feedback.json in the workspace.

Usage:
    python eval-viewer/generate_review.py <workspace-path> [--port PORT] [--skill-name NAME]
    python eval-viewer/generate_review.py <workspace-path> --previous-workspace <prev-workspace>
    python eval-viewer/generate_review.py <workspace-path> --benchmark <workspace>/benchmark.json
    python eval-viewer/generate_review.py <workspace-path> --static <output.html>

--static writes a standalone HTML file instead of starting a server — use
this on Cowork or any headless/no-browser environment. Generate the viewer
BEFORE self-evaluating outputs on Cowork (see SKILL.md's surface-aware eval
section), so the human sees results as soon as they exist.

Beyond the Python stdlib this shells out to `lsof`, to find what is already
holding the requested port; without it the port check is skipped with a
note. Reclaiming a held port additionally reads /proc, so it works only on
Linux — see _is_own_process.
"""

# Required for the builtin-generic annotations used throughout this file
# (`list[dict]`, `dict[str, str] | None`). README's stated minimum is Python
# 3.8, where those are a TypeError at import time rather than at call time —
# so without this the module cannot be imported at all on 3.8. Every other
# module in this project already carries it; this one was the omission, and
# went unnoticed because nothing imported it until it gained tests.
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import signal
import subprocess
import sys
import time
import webbrowser
from functools import partial
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Files to exclude from output listings
METADATA_FILES = {"transcript.md", "user_notes.md", "metrics.json"}

# Extensions we render as inline text
TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".yaml", ".yml", ".xml", ".html", ".css", ".sh", ".rb", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".hpp", ".sql", ".r", ".toml",
}

# Extensions we render as inline images
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

# MIME type overrides for common types
MIME_OVERRIDES = {
    ".svg": "image/svg+xml",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def get_mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def find_runs(workspace: Path) -> list[dict]:
    """Recursively find directories that contain an outputs/ subdirectory."""
    runs: list[dict] = []
    _find_runs_recursive(workspace, workspace, runs)
    runs.sort(key=lambda r: (r.get("eval_id", float("inf")), r["id"]))
    return runs


def _find_runs_recursive(root: Path, current: Path, runs: list[dict]) -> None:
    if not current.is_dir():
        return
    outputs_dir = current / "outputs"
    if outputs_dir.is_dir():
        run = build_run(root, current)
        if run:
            runs.append(run)
        return
    skip = {"node_modules", ".git", "__pycache__", "skill", "inputs"}
    for child in sorted(current.iterdir()):
        if child.is_dir() and child.name not in skip:
            _find_runs_recursive(root, child, runs)


def build_run(root: Path, run_dir: Path) -> dict | None:
    """Build a run dict with prompt, outputs, and grading data."""
    prompt = ""
    eval_id = None

    for candidate in [run_dir / "eval_metadata.json", run_dir.parent / "eval_metadata.json"]:
        if candidate.exists():
            try:
                metadata = json.loads(candidate.read_text())
                prompt = metadata.get("prompt", "")
                eval_id = metadata.get("eval_id")
            except (json.JSONDecodeError, OSError):
                pass
            if prompt:
                break

    if not prompt:
        for candidate in [run_dir / "transcript.md", run_dir / "outputs" / "transcript.md"]:
            if candidate.exists():
                try:
                    text = candidate.read_text()
                    match = re.search(r"## Eval Prompt\n\n([\s\S]*?)(?=\n##|$)", text)
                    if match:
                        prompt = match.group(1).strip()
                except OSError:
                    pass
                if prompt:
                    break

    if not prompt:
        prompt = "(No prompt found)"

    run_id = str(run_dir.relative_to(root)).replace("/", "-").replace("\\", "-")

    outputs_dir = run_dir / "outputs"
    output_files: list[dict] = []
    if outputs_dir.is_dir():
        for f in sorted(outputs_dir.iterdir()):
            if f.is_file() and f.name not in METADATA_FILES:
                output_files.append(embed_file(f))

    grading = None
    for candidate in [run_dir / "grading.json", run_dir.parent / "grading.json"]:
        if candidate.exists():
            try:
                grading = json.loads(candidate.read_text())
            except (json.JSONDecodeError, OSError):
                pass
            if grading:
                break

    return {"id": run_id, "prompt": prompt, "eval_id": eval_id, "outputs": output_files, "grading": grading}


def embed_file(path: Path) -> dict:
    """Read a file and return an embedded representation."""
    ext = path.suffix.lower()
    mime = get_mime_type(path)

    if ext in TEXT_EXTENSIONS:
        try:
            content = path.read_text(errors="replace")
        except OSError:
            content = "(Error reading file)"
        return {"name": path.name, "type": "text", "content": content}
    elif ext in IMAGE_EXTENSIONS:
        try:
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return {"name": path.name, "type": "error", "content": "(Error reading file)"}
        return {"name": path.name, "type": "image", "mime": mime, "data_uri": f"data:{mime};base64,{b64}"}
    elif ext == ".pdf":
        try:
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return {"name": path.name, "type": "error", "content": "(Error reading file)"}
        return {"name": path.name, "type": "pdf", "data_uri": f"data:{mime};base64,{b64}"}
    elif ext == ".xlsx":
        try:
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return {"name": path.name, "type": "error", "content": "(Error reading file)"}
        return {"name": path.name, "type": "xlsx", "data_b64": b64}
    else:
        try:
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return {"name": path.name, "type": "error", "content": "(Error reading file)"}
        return {"name": path.name, "type": "binary", "mime": mime, "data_uri": f"data:{mime};base64,{b64}"}


def load_previous_iteration(workspace: Path) -> dict[str, dict]:
    """Load previous iteration's feedback and outputs, keyed by run_id."""
    result: dict[str, dict] = {}

    feedback_map: dict[str, str] = {}
    feedback_path = workspace / "feedback.json"
    if feedback_path.exists():
        try:
            data = json.loads(feedback_path.read_text())
            feedback_map = {
                r["run_id"]: r["feedback"] for r in data.get("reviews", []) if r.get("feedback", "").strip()
            }
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    for run in find_runs(workspace):
        result[run["id"]] = {"feedback": feedback_map.get(run["id"], ""), "outputs": run.get("outputs", [])}

    for run_id, fb in feedback_map.items():
        if run_id not in result:
            result[run_id] = {"feedback": fb, "outputs": []}

    return result


def generate_html(runs: list[dict], skill_name: str, previous: dict[str, dict] | None = None, benchmark: dict | None = None) -> str:
    """Generate the complete standalone HTML page with embedded data."""
    template_path = Path(__file__).parent / "viewer.html"
    template = template_path.read_text()

    previous_feedback: dict[str, str] = {}
    previous_outputs: dict[str, list[dict]] = {}
    if previous:
        for run_id, data in previous.items():
            if data.get("feedback"):
                previous_feedback[run_id] = data["feedback"]
            if data.get("outputs"):
                previous_outputs[run_id] = data["outputs"]

    embedded = {
        "skill_name": skill_name, "runs": runs,
        "previous_feedback": previous_feedback, "previous_outputs": previous_outputs,
    }
    if benchmark:
        embedded["benchmark"] = benchmark

    return template.replace("/*__EMBEDDED_DATA__*/", f"const EMBEDDED_DATA = {_json_for_script_block(embedded)};")


def _json_for_script_block(data) -> str:
    """Serialize `data` as JSON that is safe to inline inside a <script> tag.

    json.dumps alone is not enough here. Inside an HTML <script> element the
    parser is still scanning for markup, so a JSON *string value* containing
    the literal text `</script>` closes the element early and everything
    after it is parsed as HTML — in this file's case, attacker-chosen HTML in
    a page the viewer opens in the user's browser, same-origin with the local
    server's file-writing POST /api/feedback endpoint. `<!--` can likewise
    flip the parser into a comment-like state.

    This matters because `data` is not trusted input: it carries raw model
    output from eval runs and the contents of whatever third-party skill is
    under review. Escaping every `<` as \u003c is the standard fix and is
    sufficient — it neutralizes `</script>`, `<!--` and `<script` alike, and
    JSON.parse decodes \u003c straight back to `<`, so the data round-trips
    unchanged.

    U+2028 and U+2029 are handled for a different reason: both are valid
    inside a JSON string but are line terminators in JavaScript source, so an
    unescaped one is a syntax error in the emitted literal. json.dumps'
    default ensure_ascii=True already escapes them, so those two replacements
    are currently no-ops — they are kept so that switching to
    ensure_ascii=False (a reasonable-looking change, for smaller output or
    readable non-ASCII) cannot quietly reintroduce the breakage.
    """
    return (
        json.dumps(data)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


# ---------------------------------------------------------------------------
# HTTP server (stdlib only, zero dependencies)
# ---------------------------------------------------------------------------


def _read_proc_cmdline(pid: int) -> str | None:
    """Return /proc/<pid>/cmdline's raw bytes as text, or None if unreadable.

    None means "could not determine", never "empty command line" — callers
    must treat it as a failure to verify, not as evidence of anything.
    """
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace")
    except OSError:
        return None


def _is_own_process(pid: int, read_cmdline=None) -> bool:
    """Is `pid` another instance of *this* script?

    Compares this file's resolved path, and its bare filename, against the
    argv entries in /proc/<pid>/cmdline. A match means the port is held by a
    previous run of the viewer, which is ours to reclaim.

    Returns False on any failure to read or parse — an unreadable cmdline, a
    process owned by another user, a PID that has already exited, or a
    platform without /proc. False here means "not verified", and callers must
    treat it that way: the safe response to an unidentified process is to
    leave it alone, not to assume it is ours.

    PLATFORM LIMITATION: /proc/<pid>/cmdline is Linux-only. On macOS, and
    anywhere else without procfs, no PID can ever be verified, so this always
    returns False and _kill_port will refuse to kill anything — including the
    viewer's own previous instance. That is deliberate: silently falling back
    to killing whatever holds the port is the behaviour this check exists to
    remove, and being unable to auto-reclaim a port is a much smaller problem
    than terminating an unrelated process. The user is told to free the port
    by hand, or to pass a different --port.
    """
    reader = read_cmdline if read_cmdline is not None else _read_proc_cmdline
    raw = reader(pid)
    if not raw:
        return False
    # cmdline is NUL-separated; a trailing NUL yields a final empty field.
    argv = [part for part in raw.split("\0") if part]
    if not argv:
        return False
    try:
        own_path = str(Path(__file__).resolve())
    except OSError:
        return False
    own_name = Path(__file__).name
    for entry in argv:
        if entry == own_path or Path(entry).name == own_name:
            return True
    return False


def _kill_port(port: int, is_own_process=_is_own_process) -> None:
    """Free `port`, but only by terminating this script's own prior instances.

    Anything else holding the port is somebody else's process — a dev server,
    a database, an unrelated tool the user is depending on. Terminating it to
    claim a port is not a tradeoff worth making silently, so an unverified
    holder is a hard stop: the PIDs are named and the process exits non-zero
    rather than sending a signal on a guess.

    See _is_own_process for the procfs-only limitation on how "ours" is
    established.
    """
    try:
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        return
    except FileNotFoundError:
        print("Note: lsof not found, cannot check if port is in use", file=sys.stderr)
        return

    ours: list[int] = []
    unrecognized: list[str] = []
    for pid_str in result.stdout.strip().split("\n"):
        pid_str = pid_str.strip()
        if not pid_str:
            continue
        # Kept per-PID rather than hoisted into a comprehension on purpose:
        # lsof can emit a line that isn't a PID (a warning, a header on some
        # builds), and one such line must not take down the whole function.
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        if is_own_process(pid):
            ours.append(pid)
        else:
            unrecognized.append(pid_str)

    if unrecognized:
        listed = ", ".join(unrecognized)
        if not Path("/proc").is_dir():
            print(
                f"Error: port {port} is in use by PID(s) {listed}, and process ownership cannot be "
                f"verified on this platform (no /proc). Free port {port} manually, or rerun with "
                f"--port <other>.",
                file=sys.stderr,
            )
        else:
            print(
                f"Error: port {port} is held by PID(s) {listed}, which are not instances of this "
                f"script. Refusing to terminate an unrelated process. Free port {port} manually, "
                f"or rerun with --port <other>.",
                file=sys.stderr,
            )
        sys.exit(1)

    for pid in ours:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if ours:
        time.sleep(0.5)


class ReviewHandler(BaseHTTPRequestHandler):
    """Serves the review HTML and handles feedback saves.

    Regenerates the HTML on each page load so refreshing the browser picks up
    new eval outputs without restarting the server.
    """

    def __init__(self, workspace: Path, skill_name: str, feedback_path: Path, previous: dict[str, dict], benchmark_path: Path | None, *args, **kwargs):
        self.workspace = workspace
        self.skill_name = skill_name
        self.feedback_path = feedback_path
        self.previous = previous
        self.benchmark_path = benchmark_path
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            runs = find_runs(self.workspace)
            benchmark = None
            if self.benchmark_path and self.benchmark_path.exists():
                try:
                    benchmark = json.loads(self.benchmark_path.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            content = generate_html(runs, self.skill_name, self.previous, benchmark).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/feedback":
            data = self.feedback_path.read_bytes() if self.feedback_path.exists() else b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/feedback":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                if not isinstance(data, dict) or "reviews" not in data:
                    raise ValueError("Expected JSON object with 'reviews' key")
                self.feedback_path.write_text(json.dumps(data, indent=2) + "\n")
                resp = b'{"ok":true}'
                self.send_response(200)
            except (json.JSONDecodeError, OSError, ValueError) as e:
                resp = json.dumps({"error": str(e)}).encode()
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        pass  # keep the terminal clean


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and serve eval review")
    parser.add_argument("workspace", type=Path, help="Path to workspace directory")
    parser.add_argument("--port", "-p", type=int, default=3117, help="Server port (default: 3117)")
    parser.add_argument("--skill-name", "-n", type=str, default=None, help="Skill name for header")
    parser.add_argument("--previous-workspace", type=Path, default=None, help="Previous iteration's workspace, for old outputs/feedback context")
    parser.add_argument("--benchmark", type=Path, default=None, help="Path to benchmark.json for the Benchmark tab")
    parser.add_argument("--static", "-s", type=Path, default=None, help="Write standalone HTML here instead of starting a server (Cowork/headless)")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        print(f"Error: {workspace} is not a directory", file=sys.stderr)
        sys.exit(1)

    runs = find_runs(workspace)
    if not runs:
        print(f"No runs found in {workspace}", file=sys.stderr)
        sys.exit(1)

    skill_name = args.skill_name or workspace.name.replace("-workspace", "")
    feedback_path = workspace / "feedback.json"

    previous: dict[str, dict] = {}
    if args.previous_workspace:
        previous = load_previous_iteration(args.previous_workspace.resolve())

    benchmark_path = args.benchmark.resolve() if args.benchmark else None
    benchmark = None
    if benchmark_path and benchmark_path.exists():
        try:
            benchmark = json.loads(benchmark_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if args.static:
        html_out = generate_html(runs, skill_name, previous, benchmark)
        args.static.parent.mkdir(parents=True, exist_ok=True)
        args.static.write_text(html_out)
        print(f"\n  Static viewer written to: {args.static}\n")
        sys.exit(0)

    port = args.port
    _kill_port(port)
    handler = partial(ReviewHandler, workspace, skill_name, feedback_path, previous, benchmark_path)
    try:
        server = HTTPServer(("127.0.0.1", port), handler)
    except OSError:
        server = HTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]

    url = f"http://localhost:{port}"
    print(f"\n  Eval Viewer\n  {'-' * 35}\n  URL:       {url}\n  Workspace: {workspace}\n  Feedback:  {feedback_path}")
    if previous:
        print(f"  Previous:  {args.previous_workspace} ({len(previous)} runs)")
    if benchmark_path:
        print(f"  Benchmark: {benchmark_path}")
    print("\n  Press Ctrl+C to stop.\n")

    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
