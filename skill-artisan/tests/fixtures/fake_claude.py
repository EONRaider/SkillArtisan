"""A stand-in for the `claude` CLI, for description_optimizer.py's tests.

Installed on PATH as `claude` by test_description_optimizer_isolation.py.
Never spends usage and never talks to the network. Behaviour is selected by
FAKE_CLAUDE_MODE, and every invocation writes one JSON record to
$FAKE_CLAUDE_LOG_DIR/<pid>.json describing what it saw, so a test can assert
on the environment each child was given, not just on the return value.

Modes (trigger runs, i.e. `-p <query> --output-format stream-json`):
  trigger      "Think" for FAKE_CLAUDE_THINK_SECONDS, then invoke, via the
               Skill tool, the first skill listed in the cwd's
               .claude/skills/ at that moment — as a model does when it
               picks one of several identically-described copies. Then keep
               "running the skill" for FAKE_CLAUDE_SKILL_SECONDS and record
               that it finished; a child stopped early never records that.
  no-trigger   Answer without calling any tool and exit.
  hang         Emit nothing and sleep past any sane test timeout.

Any invocation whose --model is not in FAKE_CLAUDE_MODELS (comma-separated,
default "opus,sonnet,haiku") exits 1 with the CLI's style of error, as the
real CLI does for a model id it doesn't know.
"""
import json
import os
import sys
import time
from pathlib import Path


def _arg(flag):
    argv = sys.argv[1:]
    return argv[argv.index(flag) + 1] if flag in argv else None


def _emit(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def main():
    log_dir = Path(os.environ["FAKE_CLAUDE_LOG_DIR"])
    record_path = log_dir / f"{os.getpid()}.json"
    skills_dir = Path.cwd() / ".claude" / "skills"

    def list_skills():
        return sorted(p.name for p in skills_dir.iterdir()) if skills_dir.is_dir() else []

    record = {
        "argv": sys.argv[1:],
        "cwd": str(Path.cwd()),
        "skills_seen": list_skills(),
        "started": time.time(),
    }

    def save(**extra):
        record.update(extra)
        record_path.write_text(json.dumps(record))

    save()

    allowed_models = os.environ.get("FAKE_CLAUDE_MODELS", "opus,sonnet,haiku").split(",")
    model = _arg("--model")
    if model is not None and model not in allowed_models:
        sys.stderr.write(f"There's an issue with the selected model ({model}). It may not exist.\n")
        save(exit=1)
        return 1

    if _arg("--output-format") == "text":
        # A rewrite or preflight call: prompt on stdin, text out.
        sys.stdin.read()
        sys.stdout.write("<new_description>rewritten</new_description>\n")
        save(exit=0)
        return 0

    mode = os.environ.get("FAKE_CLAUDE_MODE", "no-trigger")
    _emit({"type": "system", "subtype": "init", "skills": record["skills_seen"]})
    if mode == "hang":
        time.sleep(600)
        return 0
    time.sleep(float(os.environ.get("FAKE_CLAUDE_THINK_SECONDS", "0")))
    skills = list_skills()
    save(skills_seen=skills, decided=time.time())
    if mode == "trigger" and skills:
        chosen = skills[0]
        save(invoked=chosen)
        _emit({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": chosen}},
        ]}})
        time.sleep(float(os.environ.get("FAKE_CLAUDE_SKILL_SECONDS", "2")))
        save(skill_finished=True)
        _emit({"type": "result", "subtype": "success"})
        return 0
    _emit({"type": "assistant", "message": {"content": [{"type": "text", "text": "Sure."}]}})
    _emit({"type": "result", "subtype": "success"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
