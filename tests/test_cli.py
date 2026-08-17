"""Tests for chronicle's CLI argument parsing and main() integration."""

from pathlib import Path

import chronicle
import pytest


def test_parse_args_no_positional(monkeypatch):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle"])
    args = chronicle.parse_args()
    assert args.config is None


def test_parse_args_explicit_config(monkeypatch):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "--config", "/tmp/x.conf"])
    args = chronicle.parse_args()
    assert args.config == Path("/tmp/x.conf")


def test_parse_args_help(monkeypatch, capsys):
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", "-h"])
    with pytest.raises(SystemExit) as exc_info:
        chronicle.parse_args()
    assert exc_info.value.code == 0
    assert "usage" in capsys.readouterr().out


def _run_main(monkeypatch, argv, editor_content="my entry"):
    """Run main() with a mocked editor returning `editor_content`."""
    monkeypatch.setattr(chronicle, "edit_entry", lambda: editor_content)
    monkeypatch.setattr(chronicle.sys, "argv", ["chronicle", *argv])
    return chronicle.main()


def test_main_creates_new_file(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)  # a Wednesday
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="my entry")

    assert rc == 0
    quarter_file = root / "2026-q3.md"
    assert quarter_file.read_text() == (
        "# 2026 Q3\n## August\n\n### 2026-08-12, Wednesday\nmy entry\n"
    )
    assert capsys.readouterr().out == "my entry\n"


def test_main_appends_to_existing_today_section(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    root.mkdir()
    quarter_file = root / "2026-q3.md"
    quarter_file.write_text(
        "# 2026 Q3\n## August\n\n### 2026-08-12, Wednesday\nfirst entry\n"
    )
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="second entry")

    assert rc == 0
    assert quarter_file.read_text() == (
        "# 2026 Q3\n## August\n\n### 2026-08-12, Wednesday\nfirst entry\nsecond entry\n"
    )


def test_main_existing_month_new_day(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    root.mkdir()
    quarter_file = root / "2026-q3.md"
    quarter_file.write_text(
        "# 2026 Q3\n## August\n\n### 2026-08-11, Tuesday\nyesterday\n"
    )
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="today's entry")

    assert rc == 0
    assert quarter_file.read_text() == (
        "# 2026 Q3\n"
        "## August\n"
        "\n"
        "### 2026-08-11, Tuesday\n"
        "yesterday\n"
        "\n"
        "### 2026-08-12, Wednesday\n"
        "today's entry\n"
    )
    # Month heading is not duplicated.
    assert quarter_file.read_text().count("## August") == 1


def test_main_trims_trailing_blank_lines(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    root.mkdir()
    quarter_file = root / "2026-q3.md"
    quarter_file.write_text(
        "# 2026 Q3\n## August\n\n### 2026-08-11, Tuesday\nyesterday\n\n\n\n"
    )
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="today's entry")

    assert rc == 0
    content = quarter_file.read_text()
    assert "\n\n\n" not in content


def test_main_empty_editor_content_no_op(monkeypatch, tmp_path, freeze_date, capsys):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="")

    assert rc == 0
    assert not (root / "2026-q3.md").exists()
    assert capsys.readouterr().out == ""


def test_main_whitespace_only_editor_content_no_op(
    monkeypatch, tmp_path, freeze_date, capsys
):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="   \n  \n")

    assert rc == 0
    assert not (root / "2026-q3.md").exists()


def test_main_strips_leading_and_trailing_newlines(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="\n\nhello world\n\n")

    assert rc == 0
    assert "hello world\n" in (root / "2026-q3.md").read_text()


def test_main_multiline_content_preserved_verbatim(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    monkeypatch.setenv(chronicle.ENV_VAR, str(root))

    rc = _run_main(monkeypatch, [], editor_content="first line\nsecond line\nthird")

    assert rc == 0
    content = (root / "2026-q3.md").read_text()
    assert "first line\nsecond line\nthird\n" in content


def test_main_explicit_config_missing_file_raises(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    missing_config = tmp_path / "does-not-exist.conf"

    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--config", str(missing_config)], editor_content="x")


def test_main_config_file_driven_root_dir(monkeypatch, tmp_path, freeze_date):
    freeze_date(2026, 8, 12)
    root = tmp_path / "journal"
    config_path = tmp_path / "chronicle.conf"
    config_path.write_text(f"[chronicle]\nroot_dir = {root}\n")

    rc = _run_main(monkeypatch, ["--config", str(config_path)], editor_content="entry")

    assert rc == 0
    assert (root / "2026-q3.md").exists()


def test_edit_entry_uses_env_editor(monkeypatch, tmp_path):
    captured = {}
    editor = tmp_path / "myeditor.sh"
    editor.write_text("#!/bin/sh\necho 'editor ran' > \"$1\"\n")
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(editor))

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        # Simulate editor writing content to the temp file path (last arg).
        with open(cmd[-1], "w") as f:
            f.write("from editor\n")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    result = chronicle.edit_entry()

    assert result == "from editor\n"
    assert captured["cmd"][0] == str(editor)


def test_edit_entry_falls_back_to_vi_when_editor_unset(monkeypatch):
    monkeypatch.delenv("EDITOR", raising=False)
    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("vi content")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    result = chronicle.edit_entry()

    assert captured["cmd"][0] == "vi"
    assert result == "vi content"


def test_edit_editor_with_args(monkeypatch, tmp_path):
    editor = tmp_path / "editor.sh"
    editor.write_text('#!/bin/sh\necho x > "$1"\n')
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", f"{editor} --flag --wait")

    captured = {}

    def fake_run(cmd, check):
        captured["cmd"] = cmd
        with open(cmd[-1], "w") as f:
            f.write("ok")

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry()

    assert captured["cmd"] == [str(editor), "--flag", "--wait", captured["cmd"][-1]]


def test_edit_entry_cleans_up_temp_file(monkeypatch):
    monkeypatch.delenv("EDITOR", raising=False)

    created_paths = []

    def fake_run(cmd, check):
        created_paths.append(cmd[-1])

    monkeypatch.setattr(chronicle.subprocess, "run", fake_run)
    chronicle.edit_entry()

    import os

    assert all(not os.path.exists(p) for p in created_paths)
