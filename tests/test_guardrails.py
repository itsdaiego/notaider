import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from code_workflow import CodeChange, CodeChunkChange, CodeWorkflow
from secrets_scan import redact_secrets
from storage import _validate_command


class FakeStorage:
    def __init__(self, app_dir: Path, storage_dir: Path):
        self.app_dir = str(app_dir)
        self.storage_dir = str(storage_dir)

    def store_code_chunks(self, filename=None):
        pass


@pytest.fixture
def workflow(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    storage_dir = tmp_path / "db"
    storage_dir.mkdir()
    return CodeWorkflow(storage=FakeStorage(app_dir, storage_dir), model="gpt-4o-mini")


@pytest.mark.parametrize(
    "filename",
    ["../../etc/passwd.py", "/etc/passwd.py", "sub/../../escape.py", "notes.txt"],
)
def test_codechunkchange_rejects_unsafe_filenames(filename):
    with pytest.raises(ValidationError):
        CodeChunkChange(old_code="x", new_code="y", filename=filename, chunk_name="c")


def test_codechunkchange_accepts_safe_relative_path():
    change = CodeChunkChange(old_code="x", new_code="y", filename="sub/todo.py", chunk_name="c")
    assert change.filename == "sub/todo.py"


def test_resolve_within_app_dir_blocks_traversal(workflow):
    with pytest.raises(ValueError):
        workflow._resolve_within_app_dir("../outside.py")


def test_resolve_within_app_dir_allows_normal_path(workflow):
    resolved = workflow._resolve_within_app_dir("todo.py")
    assert resolved.parent == Path(workflow.storage.app_dir).resolve()


def test_apply_change_refuses_to_escape_app_dir(workflow, tmp_path):
    outside_file = tmp_path / "secret.py"
    change = CodeChange(
        old_code="", new_code="pwned = True", filename="../secret.py", chunk_name="c"
    )

    workflow._apply_change(change, target_files={"../secret.py"})

    assert not outside_file.exists()


def test_apply_change_rejects_invalid_syntax(workflow):
    target = Path(workflow.storage.app_dir) / "broken.py"
    change = CodeChange(old_code="", new_code="def broken(:", filename="broken.py", chunk_name="c")

    workflow._apply_change(change, target_files={"broken.py"})

    assert not target.exists()


def test_apply_change_writes_valid_code_and_audit_log(workflow):
    change = CodeChange(old_code="", new_code="x = 1", filename="new_file.py", chunk_name="c")

    workflow._apply_change(change, target_files={"new_file.py"})

    written = Path(workflow.storage.app_dir) / "new_file.py"
    assert written.exists()
    ast.parse(written.read_text())

    audit_path = Path(workflow.storage.storage_dir) / "audit_log.jsonl"
    entries = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert entries[-1]["filename"] == "new_file.py"
    assert entries[-1]["new_code"] == "x = 1"


def test_redact_secrets_masks_api_key():
    code = 'api_key = "sk-ABCDEFGHIJKLMNOP"\nprint("hello")'

    redacted, count = redact_secrets(code)

    assert count == 1
    assert "sk-ABCDEFGHIJKLMNOP" not in redacted
    assert "print" in redacted


def test_redact_secrets_masks_private_key_block():
    code = "-----BEGIN RSA PRIVATE KEY-----\nMIIC...\n-----END RSA PRIVATE KEY-----\n"

    redacted, count = redact_secrets(code)

    assert count == 1
    assert "MIIC" not in redacted


def test_redact_secrets_leaves_normal_code_untouched():
    code = "def add(a, b):\n    return a + b\n"

    redacted, count = redact_secrets(code)

    assert redacted == code
    assert count == 0


@pytest.mark.parametrize(
    "command",
    [
        "grep -rn foo .",
        "find . -name '*.py'",
        "cat todo.py",
        "grep foo . | head",
        "ls -la sub",
    ],
)
def test_validate_command_allows_safe_readonly_commands(command):
    assert _validate_command(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf .",
        "touch new.py",
        "echo hi > out.py",
        "cat ../../etc/passwd",
        "cat /etc/passwd",
        "grep foo . && rm -rf .",
        "grep foo . ; rm -rf .",
        "grep foo . || rm -rf .",
        "find . -delete",
        "find . -exec rm {} \\;",
        "grep `whoami` .",
        "grep $(whoami) .",
    ],
)
def test_validate_command_blocks_unsafe_commands(command):
    assert _validate_command(command) is not None
