#!/usr/bin/env python3
"""Two-tier security scanner for a skill directory, plus the packaging gate
that depends on it.

Verified directly against a real gitleaks install and a live scan while
building this — the command, JSON-to-file requirement, and severity
classification below match observed behavior, not just documentation.

**Tier 1 — default mode gates packaging.** Runs gitleaks only:

    gitleaks detect --source <path> --report-format json --report-path <tmp> --no-git

Gitleaks writes JSON to a file, not stdout (`--report-path` is required —
Windows has no `/dev/stdout`), so this script uses a temp file and removes it
after reading. Severity isn't gitleaks-native: it's a keyword match against
each finding's RuleID — any of api/key/token/password/secret/credential
(case-insensitive substring) is CRITICAL, everything else is HIGH. Exit
codes: 0 clean, 1 high-severity present, 2 critical present, 3 gitleaks not
installed, 4 scan error.

**Tier 2 — `--verbose` adds pattern checks as an educational review layer,
not a stricter default gate.** Absolute user paths, exposed emails, insecure
http:// URLs, dangerous code patterns, and unsafe command interpolation.
Only HIGH pattern findings affect the exit code alongside gitleaks; MEDIUM is
informational only, never blocking. Don't collapse this into one gate — the
two-tier split is the whole point (see references/security-checklist.md).

**Security marker + tamper detection.** A clean default-mode scan writes
`.security-scan-passed`: a SHA256 hash over every non-excluded file's
relative path (UTF-8, null-separated) plus its raw content (null-separated),
sorted by path for determinism, written atomically (temp file + os.replace,
since packaging reads this concurrently). `--package` refuses to run if the
marker is missing or its hash no longer matches current content.

Usage:
    python scripts/security_scan.py <skill-path>              # gitleaks only
    python scripts/security_scan.py <skill-path> --verbose     # + pattern checks
    python scripts/security_scan.py <skill-path> --package <output-dir>
    python scripts/security_scan.py <skill-path> --package <output-dir> --dry-run
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

MARKER_FILENAME = ".security-scan-passed"

CRITICAL_KEYWORDS = ("api", "key", "token", "password", "secret", "credential")

# Directories always excluded from scanning, hashing, and packaging,
# regardless of .skillignore content.
ALWAYS_EXCLUDE_DIRS = {".git", "__pycache__", "node_modules"}

PATTERN_SCAN_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".md", ".yml", ".yaml", ".json", ".jsonl", ".toml",
}

# --- Pattern checks (--verbose only) ---------------------------------------

ABS_PATH_PATTERNS = [
    re.compile(r"/home/[A-Za-z0-9_.-]+"),
    re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    re.compile(r"C:\\Users\\[A-Za-z0-9_.-]+"),
]

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
EMAIL_EXCEPTIONS = ("example.com", "test.com", "localhost", "noreply@anthropic.com")

HTTP_URL_PATTERN = re.compile(r"http://[^\s\"'<>)]+")
HTTP_URL_EXCEPTIONS = ("localhost", "127.0.0.1", "0.0.0.0", "example.com")  # NOT test.com — that's email-only

DANGEROUS_CODE_PATTERNS = [
    (re.compile(r"os\.system\("), "os.system( call — arbitrary shell execution"),
    (re.compile(r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True"), "subprocess ... shell=True — shell injection risk"),
    (re.compile(r"^\s*import pickle\b", re.MULTILINE), "import pickle — arbitrary code execution on untrusted input"),
    (re.compile(r"pickle\.load\("), "pickle.load( — arbitrary code execution on untrusted input"),
]

# references/script-design.md checks: bundled scripts must be non-interactive
# and must document a real interface, not just dump ad hoc prose to stdout.
INTERACTIVE_INPUT_PATTERNS = [
    re.compile(r"\binput\s*\("),
    re.compile(r"\braw_input\s*\("),
    re.compile(r"\bread\s+-p\b"),  # bash: read -p "prompt" var, with no </dev/null guard
]

# Row 38 (prior art: tripleyak/SkillForge, distinct from daymade's pattern set):
# building a shell command by interpolating unsanitized input via f-string/.format()/concatenation.
UNSAFE_INTERPOLATION_PATTERNS = [
    re.compile(r"subprocess\.[A-Za-z_]+\(\s*f[\"']"),          # f-string passed straight to subprocess
    re.compile(r"os\.system\(\s*f[\"']"),
    re.compile(r"os\.system\([^)]*%\s*\("),                     # % string formatting into os.system
    re.compile(r"os\.system\([^)]*\.format\("),
]


def iter_scannable_files(skill_path: Path, skillignore_patterns: list[str]):
    for path in sorted(skill_path.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_path)
        if any(part in ALWAYS_EXCLUDE_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if is_hidden(rel):
            continue
        if matches_skillignore(rel, skillignore_patterns):
            continue
        yield path, rel


def is_hidden(rel_path: Path) -> bool:
    return any(part.startswith(".") for part in rel_path.parts)


def load_skillignore(skill_path: Path) -> list[str]:
    ignore_file = skill_path / ".skillignore"
    if not ignore_file.exists():
        return []
    patterns = []
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def matches_skillignore(rel_path: Path, patterns: list[str]) -> bool:
    rel_str = rel_path.as_posix()
    for pattern in patterns:
        if pattern.endswith("/"):
            dirname = pattern.rstrip("/")
            if dirname in rel_path.parts[:-1] or rel_str.startswith(dirname + "/"):
                return True
        elif "/" in pattern:
            if fnmatch.fnmatch(rel_str, pattern):
                return True
        else:
            if fnmatch.fnmatch(rel_path.name, pattern) or any(fnmatch.fnmatch(part, pattern) for part in rel_path.parts):
                return True
    return False


def compute_content_hash(skill_path: Path) -> str:
    """SHA256 over every non-excluded file's (relative path, content), sorted
    by path, null-separated. Deterministic — same content always hashes the
    same, regardless of filesystem iteration order."""
    patterns = load_skillignore(skill_path)
    hasher = hashlib.sha256()
    for _, rel in iter_scannable_files(skill_path, patterns):
        full = skill_path / rel
        hasher.update(rel.as_posix().encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(full.read_bytes())
        hasher.update(b"\x00")
    return hasher.hexdigest()


def write_marker(skill_path: Path, content_hash: str) -> None:
    """Atomic write: temp file + os.replace, since packaging may read this
    concurrently with another scan in progress elsewhere."""
    marker = {"hash": content_hash, "algorithm": "sha256"}
    fd, tmp_path = tempfile.mkstemp(dir=skill_path, prefix=f".{MARKER_FILENAME}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(marker, f)
        os.replace(tmp_path, skill_path / MARKER_FILENAME)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def verify_marker(skill_path: Path) -> tuple[bool, str]:
    marker_path = skill_path / MARKER_FILENAME
    if not marker_path.exists():
        return False, f"No {MARKER_FILENAME} found — run a clean security scan before packaging"
    try:
        marker = json.loads(marker_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Could not read {MARKER_FILENAME}: {e}"
    current_hash = compute_content_hash(skill_path)
    if marker.get("hash") != current_hash:
        return False, "Skill content changed since last security scan — rerun the scan before packaging"
    return True, "Marker valid"


# --- Gitleaks (tier 1) -------------------------------------------------------


def run_gitleaks(skill_path: Path) -> tuple[list[dict], bool, bool]:
    """Returns (findings, gitleaks_installed, scan_error)."""
    if not shutil.which("gitleaks"):
        return [], False, False

    fd, report_path = tempfile.mkstemp(prefix="gitleaks-report-", suffix=".json")
    os.close(fd)
    try:
        result = subprocess.run(
            ["gitleaks", "detect", "--source", str(skill_path), "--report-format", "json",
             "--report-path", report_path, "--no-git"],
            capture_output=True, text=True, timeout=120,
        )
        # gitleaks exit codes: 0 clean, 1 leaks found. Anything else is a real error.
        if result.returncode not in (0, 1):
            return [], True, True
        try:
            findings = json.loads(Path(report_path).read_text() or "[]")
        except json.JSONDecodeError:
            return [], True, True
        return findings or [], True, False
    except subprocess.TimeoutExpired:
        return [], True, True
    finally:
        Path(report_path).unlink(missing_ok=True)


def classify_gitleaks_severity(rule_id: str) -> str:
    lowered = rule_id.lower()
    return "CRITICAL" if any(kw in lowered for kw in CRITICAL_KEYWORDS) else "HIGH"


# --- Pattern checks (tier 2, --verbose) -------------------------------------


def docstring_line_numbers(text: str) -> set[int]:
    """1-indexed line numbers that fall inside a triple-quoted Python string
    literal (a docstring, most often). Used to keep the interactive-input
    check from matching ordinary English prose written inside one — found
    via real-world testing (daymade/claude-code-skills' excel-automation:
    a docstring reading "Style a cell as user input (blue font, green
    fill)" matched \\binput\\s*\\( even though it's not a real input() call,
    the same false-positive shape already fixed once for a bash comment —
    it recurs here in a different, non-comment context a single
    #-line-skip doesn't cover)."""
    lines = set()
    for m in re.finditer(r'("""|\'\'\').*?\1', text, re.DOTALL):
        start_line = text.count("\n", 0, m.start()) + 1
        end_line = text.count("\n", 0, m.end()) + 1
        lines.update(range(start_line, end_line + 1))
    return lines


def run_pattern_checks(skill_path: Path) -> list[dict]:
    patterns = load_skillignore(skill_path)
    findings = []
    for path, rel in iter_scannable_files(skill_path, patterns):
        if path.suffix.lower() not in PATTERN_SCAN_EXTENSIONS:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        lines = text.split("\n")
        docstring_lines = docstring_line_numbers(text) if path.suffix.lower() == ".py" else set()

        for lineno, line in enumerate(lines, start=1):
            for abs_pattern in ABS_PATH_PATTERNS:
                if abs_pattern.search(line):
                    findings.append({"file": str(rel), "line": lineno, "severity": "HIGH", "check": "absolute-user-path", "detail": line.strip()[:160]})

            for match in EMAIL_PATTERN.finditer(line):
                email = match.group(0)
                if not any(exc in email.lower() for exc in EMAIL_EXCEPTIONS):
                    findings.append({"file": str(rel), "line": lineno, "severity": "MEDIUM", "check": "email-address", "detail": email})

            for match in HTTP_URL_PATTERN.finditer(line):
                url = match.group(0)
                if not any(exc in url.lower() for exc in HTTP_URL_EXCEPTIONS):
                    findings.append({"file": str(rel), "line": lineno, "severity": "MEDIUM", "check": "insecure-http-url", "detail": url})

            for dc_pattern, desc in DANGEROUS_CODE_PATTERNS:
                if dc_pattern.search(line):
                    findings.append({"file": str(rel), "line": lineno, "severity": "HIGH", "check": "dangerous-code-pattern", "detail": desc})

            for ui_pattern in UNSAFE_INTERPOLATION_PATTERNS:
                if ui_pattern.search(line):
                    findings.append({"file": str(rel), "line": lineno, "severity": "HIGH", "check": "unsafe-command-interpolation", "detail": line.strip()[:160]})

            if (path.suffix.lower() in (".py", ".sh", ".bash")
                    and not line.lstrip().startswith("#")
                    and lineno not in docstring_lines):
                for interactive_pattern in INTERACTIVE_INPUT_PATTERNS:
                    if interactive_pattern.search(line):
                        findings.append({"file": str(rel), "line": lineno, "severity": "HIGH", "check": "blocking-interactive-input", "detail": line.strip()[:160]})

        # Per-file, not per-line: a script under scripts/ that produces output
        # but documents no real interface (references/script-design.md — every
        # bundled script must document its interface via --help). Restricted
        # to scripts/ specifically, and to files substantial enough that this
        # isn't just noise on a five-line helper.
        if "scripts" in rel.parts and path.suffix.lower() in (".py", ".sh", ".bash") and len(lines) > 10:
            has_output = bool(re.search(r"\bprint\s*\(|\becho\b", text))
            documents_interface = bool(re.search(r"argparse|click\.|typer\.|--help|getopt", text))
            if has_output and not documents_interface:
                findings.append({
                    "file": str(rel), "line": 1, "severity": "MEDIUM", "check": "no-documented-cli",
                    "detail": "produces output but references no argument-parsing/--help convention (references/script-design.md)",
                })

    return findings


# --- Packaging ---------------------------------------------------------------


def package_skill(skill_path: Path, output_dir: Path) -> Path:
    valid, reason = verify_marker(skill_path)
    if not valid:
        raise RuntimeError(reason)

    patterns = load_skillignore(skill_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_filename = output_dir / f"{skill_path.name}.skill"

    # iter_scannable_files already excludes dotfiles (is_hidden), which covers
    # .security-scan-passed itself — no separate marker exclusion needed here.
    with zipfile.ZipFile(skill_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in iter_scannable_files(skill_path, patterns):
            zf.write(path, rel.as_posix())

    return skill_filename


# --- CLI ---------------------------------------------------------------------


def print_findings(findings: list[dict], gitleaks_findings: list[dict]) -> None:
    for f in gitleaks_findings:
        sev = classify_gitleaks_severity(f.get("RuleID", ""))
        print(f"  [{sev}] gitleaks:{f.get('RuleID', '?')} — {f.get('File', '?')}:{f.get('StartLine', '?')} — {f.get('Description', '')}")
    for f in findings:
        print(f"  [{f['severity']}] {f['check']} — {f['file']}:{f['line']} — {f['detail']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-tier security scanner + packaging gate for a skill directory")
    parser.add_argument("skill_path", help="Path to the skill directory")
    parser.add_argument("--verbose", action="store_true", help="Also run pattern checks (educational layer, HIGH findings only affect exit code)")
    parser.add_argument("--package", metavar="OUTPUT_DIR", default=None, help="Package the skill into OUTPUT_DIR/<name>.skill after verifying the security marker")
    parser.add_argument("--dry-run", action="store_true", help="With --package: report what would happen without writing the .skill file")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON instead of a text report")
    args = parser.parse_args()

    skill_path = Path(args.skill_path).resolve()
    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}", file=sys.stderr)
        sys.exit(2)

    if args.package:
        try:
            if args.dry_run:
                valid, reason = verify_marker(skill_path)
                print(reason)
                sys.exit(0 if valid else 1)
            output_path = package_skill(skill_path, Path(args.package))
            print(f"Packaged: {output_path}")
            sys.exit(0)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    gitleaks_findings, gitleaks_installed, scan_error = run_gitleaks(skill_path)
    if not gitleaks_installed:
        print("Error: gitleaks not installed — see https://github.com/gitleaks/gitleaks", file=sys.stderr)
        sys.exit(3)
    if scan_error:
        print("Error: gitleaks scan failed", file=sys.stderr)
        sys.exit(4)

    pattern_findings = run_pattern_checks(skill_path) if args.verbose else []
    high_pattern_findings = [f for f in pattern_findings if f["severity"] == "HIGH"]

    critical = [f for f in gitleaks_findings if classify_gitleaks_severity(f.get("RuleID", "")) == "CRITICAL"]
    high = [f for f in gitleaks_findings if classify_gitleaks_severity(f.get("RuleID", "")) == "HIGH"]

    if args.json:
        print(json.dumps({
            "skill_path": str(skill_path),
            "gitleaks_findings": gitleaks_findings,
            "pattern_findings": pattern_findings if args.verbose else None,
            "critical_count": len(critical),
            "high_count": len(high) + len(high_pattern_findings),
        }, indent=2))
    else:
        print(f"Scanning: {skill_path}")
        if not gitleaks_findings and not pattern_findings:
            print("  No findings.")
        else:
            print_findings(pattern_findings, gitleaks_findings)
        if args.verbose:
            medium_count = len([f for f in pattern_findings if f["severity"] == "MEDIUM"])
            print(f"\n  ({medium_count} MEDIUM pattern finding(s) are informational only — do not affect the exit code)")

    # Exit code driven by gitleaks alone in default mode; --verbose adds HIGH pattern findings.
    clean = not gitleaks_findings and not high_pattern_findings
    if clean:
        write_marker(skill_path, compute_content_hash(skill_path))
        # --json promises pure JSON on stdout (script-design.md's stdout/stderr
        # split) — this human-readable confirmation was printing to stdout
        # unconditionally, corrupting that contract on every clean scan.
        # Found while aggregating 12 --json scans for the Best-in-Market
        # Scorecard's Axis 3: 11 of 12 failed to parse for exactly this
        # reason (the one dirty scan, with no clean-scan text appended,
        # parsed fine — the signal that gave this away).
        out = sys.stderr if args.json else sys.stdout
        print(f"\nClean scan — wrote {MARKER_FILENAME}.", file=out)
        print("Reminder: this is a keyword-based gate only. It does not catch real project/person names,", file=out)
        print("non-English content (gitleaks does not cover CJK), or verbatim lines lifted from real", file=out)
        print("transcripts — none of that has a secret signature to match. Before publishing to a public", file=out)
        print("repo, read the skill yourself — see references/sanitization-checklist.md.", file=out)
        sys.exit(0)

    if critical:
        sys.exit(2)
    if high or high_pattern_findings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
